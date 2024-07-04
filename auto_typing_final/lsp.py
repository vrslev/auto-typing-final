from collections.abc import Iterable
from typing import TypedDict, cast

from ast_grep_py import Edit, SgNode, SgRoot
from lsprotocol.types import (
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
    content: str
    location: Location
    end_location: Location


class Fix(TypedDict):
    message: str
    edits: list[DiagnosticEdit]


class DiagnosticData(TypedDict):
    fix: Fix


def make_diagnostic_edits(nodes_and_edits: Iterable[tuple[SgNode, Edit]]) -> Iterable[DiagnosticEdit]:
    for node, edit in nodes_and_edits:
        range_ = node.range()
        yield DiagnosticEdit(
            content=edit.inserted_text,
            location=Location(row=range_.start.line, column=range_.start.column),
            end_location=Location(row=range_.end.line, column=range_.end.column),
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


def make_code_actions(diagnostics: list[Diagnostic]) -> Iterable[CodeAction]:
    for _diagnostic in diagnostics:
        yield CodeAction()


@LSP_SERVER.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(code_action_kinds=[CodeActionKind.QuickFix, CodeActionKind.SourceFixAll], resolve_provider=True),
)
async def code_action(params: CodeActionParams) -> list[CodeAction] | None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    code_actions = []
    for diagnostic in params.context.diagnostics:
        if diagnostic.source != "auto-typing-final":
            continue
        data = cast(DiagnosticData, diagnostic.data)
        fix = data["fix"]
        code_actions.append(
            CodeAction(
                title=fix["message"],
                kind=CodeActionKind.QuickFix,
                data=params.text_document.uri,
                edit=WorkspaceEdit(
                    document_changes=[
                        TextDocumentEdit(
                            text_document=OptionalVersionedTextDocumentIdentifier(
                                uri=text_document.uri, version=text_document.version
                            ),
                            edits=[
                                TextEdit(
                                    range=Range(
                                        start=Position(
                                            line=edit["location"]["row"],
                                            character=edit["location"]["column"],
                                        ),
                                        end=Position(
                                            line=edit["end_location"]["row"],
                                            character=edit["end_location"]["column"],
                                        ),
                                    ),
                                    new_text=edit["content"],
                                )
                                for edit in fix["edits"]
                            ],
                        )
                    ],
                ),
                diagnostics=[diagnostic],
            )
        )
    return code_actions or None


# @LSP_SERVER.feature(CODE_ACTION_RESOLVE)
# async def resolve_code_action(params: CodeAction) -> CodeAction: ...


@LSP_SERVER.feature(INITIALIZE)
def initialize(params: InitializeParams) -> None: ...


if __name__ == "__main__":
    LSP_SERVER.start_io()
