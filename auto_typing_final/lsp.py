from collections.abc import Iterable
from typing import TypedDict, cast

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

from auto_typing_final.transform import AddFinal, AppliedEdit, make_operations_from_source

LSP_SERVER = server.LanguageServer(name="auto-typing-final", version="0", max_workers=5)


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


def make_range_from_edit(edit: AppliedEdit) -> Range:
    range_ = edit.node.range()
    return Range(
        start=Position(line=range_.start.line, character=range_.start.column),
        end=Position(line=range_.end.line, character=range_.end.column),
    )


def make_diagnostic_edit(edit: AppliedEdit) -> DiagnosticEdit:
    range_ = edit.node.range()
    return DiagnosticEdit(
        new_text=edit.edit.inserted_text,
        start=Location(row=range_.start.line, column=range_.start.column),
        end=Location(row=range_.end.line, column=range_.end.column),
    )


def make_text_edit_from_diagnostic_edit(edit: DiagnosticEdit) -> TextEdit:
    return TextEdit(
        range=Range(
            start=Position(line=edit["start"]["row"], character=edit["start"]["column"]),
            end=Position(line=edit["end"]["row"], character=edit["end"]["column"]),
        ),
        new_text=edit["new_text"],
    )


def make_diagnostics(source: str) -> Iterable[Diagnostic]:
    for applied_operation in make_operations_from_source(source):
        if isinstance(applied_operation.operation, AddFinal):
            fix_message = "Add typing.Final"
            diagnostic_message = "Missing typing.Final"
        else:
            fix_message = "Remove typing.Final"
            diagnostic_message = "Unexpected typing.Final"

        fix = Fix(message=fix_message, edits=[make_diagnostic_edit(edit) for edit in applied_operation.edits])

        for applied_edit in applied_operation.edits:
            yield Diagnostic(
                range=make_range_from_edit(applied_edit),
                message=diagnostic_message,
                source="auto-typing-final",
                data=DiagnosticData(fix=fix),
            )


def make_text_edits_for_whole_document(source: str) -> Iterable[TextEdit]:
    for applied_operation in make_operations_from_source(source):
        for applied_edit in applied_operation.edits:
            yield TextEdit(range=make_range_from_edit(applied_edit), new_text=applied_edit.edit.inserted_text)


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
@LSP_SERVER.feature(TEXT_DOCUMENT_DID_SAVE)
@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_open_did_save_did_change(
    params: DidOpenTextDocumentParams | DidSaveTextDocumentParams | DidChangeTextDocumentParams,
) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    diagnostics = list(make_diagnostics(text_document.source))
    LSP_SERVER.publish_diagnostics(text_document.uri, diagnostics)


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: DidCloseTextDocumentParams) -> None:
    LSP_SERVER.publish_diagnostics(params.text_document.uri, [])


def make_quickfix_action(diagnostic: Diagnostic, text_document: TextDocument) -> CodeAction:
    data = cast(DiagnosticData, diagnostic.data)
    fix = data["fix"]

    return CodeAction(
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
            ]
        ),
        diagnostics=[diagnostic],
    )


@LSP_SERVER.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(code_action_kinds=[CodeActionKind.QuickFix, CodeActionKind.SourceFixAll], resolve_provider=True),
)
def code_action(params: CodeActionParams) -> list[CodeAction] | None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    requested_kinds = params.context.only or [CodeActionKind.QuickFix, CodeActionKind.SourceFixAll]
    our_diagnostics = [
        diagnostic for diagnostic in params.context.diagnostics if diagnostic.source == "auto-typing-final"
    ]
    actions: list[CodeAction] = []

    if CodeActionKind.QuickFix in requested_kinds:
        actions.extend(
            make_quickfix_action(diagnostic=diagnostic, text_document=text_document) for diagnostic in our_diagnostics
        )

    if CodeActionKind.SourceFixAll in requested_kinds:
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
def initialize(params: InitializeParams) -> None: ...  # noqa: ARG001


if __name__ == "__main__":
    LSP_SERVER.start_io()
