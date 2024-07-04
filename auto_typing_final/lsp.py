from collections.abc import Iterable
from typing import TypedDict, cast

from ast_grep_py import Edit, SgNode, SgRoot
from lsprotocol.types import (
    CODE_ACTION_RESOLVE,
    INITIALIZE,
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    CodeAction,
    CodeActionKind,
    CodeActionOptions,
    CodeActionParams,
    Diagnostic,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    InitializeParams,
    OptionalVersionedTextDocumentIdentifier,
    Position,
    Range,
    TextDocumentEdit,
    TextEdit,
    WorkspaceEdit,
)
from pygls import server
from pygls.workspace import TextDocument

from auto_typing_final.finder import find_definitions_in_module
from auto_typing_final.transform import (
    AddFinal,
    make_edits_from_operation,
    make_operation_from_assignments_to_one_name,
)

LSP_SERVER = server.LanguageServer(
    name="auto-typing-final",
    version="0",
    max_workers=5,
)


class Location(TypedDict):
    row: int
    column: int


class DiagnosticEdit(TypedDict):
    new_text: str
    start: Location
    end: Location


class Fix(TypedDict):
    message: str
    edits: list[DiagnosticEdit]


class DiagnosticData(TypedDict):
    fix: Fix


def make_diagnostic_edits(nodes_and_edits: Iterable[tuple[SgNode, Edit]]) -> Iterable[DiagnosticEdit]:
    for node, edit in nodes_and_edits:
        range_ = node.range()
        yield DiagnosticEdit(
            new_text=edit.inserted_text,
            start=Location(row=range_.start.line, column=range_.start.column),
            end=Location(row=range_.end.line, column=range_.end.column),
        )


def make_diagnostics(source: str) -> Iterable[Diagnostic]:
    root = SgRoot(source, "python").root()
    for current_definitions in find_definitions_in_module(root):
        operation = make_operation_from_assignments_to_one_name(current_definitions)
        nodes_and_edits = list(make_edits_from_operation(operation))
        fix = Fix(
            message="Add typing.Final" if isinstance(operation, AddFinal) else "Remove typing.Final",
            edits=list(make_diagnostic_edits(nodes_and_edits)),
        )
        for node, _ in nodes_and_edits:
            range_ = node.range()
            yield Diagnostic(
                range=Range(
                    start=Position(line=range_.start.line, character=range_.start.column),
                    end=Position(line=range_.end.line, character=range_.end.column),
                ),
                message="Missing typing.Final" if isinstance(operation, AddFinal) else "Unexpected typing.Final",
                source="auto-typing-final",
                data=DiagnosticData(fix=fix),
            )


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(params: DidOpenTextDocumentParams) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    diagnostics = list(make_diagnostics(text_document.source))
    LSP_SERVER.publish_diagnostics(text_document.uri, diagnostics)


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: DidCloseTextDocumentParams) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    LSP_SERVER.publish_diagnostics(text_document.uri, [])


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(params: DidSaveTextDocumentParams) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    diagnostics = list(make_diagnostics(text_document.source))
    LSP_SERVER.publish_diagnostics(text_document.uri, diagnostics)


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(params: DidChangeTextDocumentParams) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    diagnostics = list(make_diagnostics(text_document.source))
    LSP_SERVER.publish_diagnostics(text_document.uri, diagnostics)


def make_text_edit_from_diagnostic_edit(edit: DiagnosticEdit) -> TextEdit:
    return TextEdit(
        range=Range(
            start=Position(line=edit["start"]["row"], character=edit["start"]["column"]),
            end=Position(line=edit["end"]["row"], character=edit["end"]["column"]),
        ),
        new_text=edit["new_text"],
    )


def make_quick_fix_code_actions(diagnostics: list[Diagnostic], text_document: TextDocument) -> Iterable[CodeAction]:
    for diagnostic in diagnostics:
        if diagnostic.source != "auto-typing-final":
            continue
        data = cast(DiagnosticData, diagnostic.data)
        fix = data["fix"]

        yield CodeAction(
            title=fix["message"],
            kind=CodeActionKind.QuickFix,
            data=text_document.uri,
            edit=WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        text_document=OptionalVersionedTextDocumentIdentifier(
                            uri=text_document.uri, version=text_document.version
                        ),
                        edits=[make_text_edit_from_diagnostic_edit(edit) for edit in fix["edits"]],
                    )
                ],
            ),
            diagnostics=[diagnostic],
        )


@LSP_SERVER.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(code_action_kinds=[CodeActionKind.QuickFix, CodeActionKind.SourceFixAll], resolve_provider=True),
)
async def code_action(params: CodeActionParams) -> list[CodeAction] | None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)

    if params.context.only:
        enabled_kinds = []
        if CodeActionKind.QuickFix in params.context.only:
            enabled_kinds.append(CodeActionKind.QuickFix)
        if CodeActionKind.SourceFixAll in params.context.only:
            enabled_kinds.append(CodeActionKind.SourceFixAll)
    else:
        enabled_kinds = [CodeActionKind.QuickFix, CodeActionKind.SourceFixAll]

    our_diagnostics = [
        diagnostic for diagnostic in params.context.diagnostics if diagnostic.source == "auto-typing-final"
    ]
    actions: list[CodeAction] = []

    if CodeActionKind.QuickFix in enabled_kinds:
        actions.extend(make_quick_fix_code_actions(diagnostics=our_diagnostics, text_document=text_document))

    if CodeActionKind.SourceFixAll in enabled_kinds:
        actions.append(
            CodeAction(
                title="auto-typing-final: Fix All",
                kind=CodeActionKind.SourceFixAll,
                data=params.text_document.uri,
                edit=None,
                diagnostics=[],
            ),
        )

    return actions or None


def make_text_edits_for_whole_document(source: str) -> Iterable[TextEdit]:
    root = SgRoot(source, "python").root()
    for current_definitions in find_definitions_in_module(root):
        operation = make_operation_from_assignments_to_one_name(current_definitions)
        for node, edit in make_edits_from_operation(operation):
            range_ = node.range()
            yield TextEdit(
                range=Range(
                    start=Position(line=range_.start.line, character=range_.start.column),
                    end=Position(line=range_.end.line, character=range_.end.column),
                ),
                new_text=edit.inserted_text,
            )


@LSP_SERVER.feature(CODE_ACTION_RESOLVE)
def resolve_code_action(params: CodeAction) -> CodeAction:
    if params.kind != CodeActionKind.SourceFixAll:
        return params

    text_document = LSP_SERVER.workspace.get_text_document(cast(str, params.data))
    params.edit = WorkspaceEdit(
        document_changes=[
            TextDocumentEdit(
                text_document=OptionalVersionedTextDocumentIdentifier(
                    uri=text_document.uri, version=text_document.version
                ),
                edits=list(make_text_edits_for_whole_document(text_document.source)),
            )
        ],
    )
    return params


@LSP_SERVER.feature(INITIALIZE)
def initialize(params: InitializeParams) -> None: ...


if __name__ == "__main__":
    LSP_SERVER.start_io()
