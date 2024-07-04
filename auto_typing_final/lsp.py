from collections.abc import Iterable
from typing import TypedDict, cast

import cattrs
from ast_grep_py import SgRoot
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

from auto_typing_final.finder import has_global_import_with_name
from auto_typing_final.transform import AddFinal, AppliedOperation, make_operations_from_root

LSP_SERVER = server.LanguageServer(name="auto-typing-final", version="0", max_workers=5)


class DiagnosticPosition(TypedDict):
    line: int
    character: int


class DiagnosticRange(TypedDict):
    start: DiagnosticPosition
    end: DiagnosticPosition


class DiagnosticTextEdit(TypedDict):
    range: DiagnosticRange
    new_text: str


class DiagnosticFix(TypedDict):
    message: str
    text_edits: list[DiagnosticTextEdit]


class DiagnosticData(TypedDict):
    fix: DiagnosticFix


def make_diagnostic_text_edits(applied_operation: AppliedOperation, has_import: bool) -> Iterable[DiagnosticTextEdit]:  # noqa: FBT001
    for edit in applied_operation.edits:
        node_range = edit.node.range()
        yield {
            "range": {
                "start": {"line": node_range.start.line, "character": node_range.start.column},
                "end": {"line": node_range.end.line, "character": node_range.end.column},
            },
            "new_text": edit.edit.inserted_text,
        }

    if isinstance(applied_operation.operation, AddFinal) and not has_import:
        yield {
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
            "new_text": "import typing\n",
        }


def make_diagnostics(source: str) -> Iterable[Diagnostic]:
    root = SgRoot(source, "python").root()
    has_import = has_global_import_with_name(root, "typing")

    for applied_operation in make_operations_from_root(root):
        if isinstance(applied_operation.operation, AddFinal):
            fix_message = f"{LSP_SERVER.name}: Add typing.Final"
            diagnostic_message = "Missing typing.Final"
        else:
            fix_message = f"{LSP_SERVER.name}: Remove typing.Final"
            diagnostic_message = "Unexpected typing.Final"

        fix = DiagnosticFix(
            message=fix_message,
            text_edits=list(make_diagnostic_text_edits(applied_operation=applied_operation, has_import=has_import)),
        )

        for applied_edit in applied_operation.edits:
            node_range = applied_edit.node.range()
            yield Diagnostic(
                range=Range(
                    start=Position(line=node_range.start.line, character=node_range.start.column),
                    end=Position(line=node_range.end.line, character=node_range.end.column),
                ),
                message=diagnostic_message,
                source=LSP_SERVER.name,
                data=DiagnosticData(fix=fix),
            )


def make_fixall_text_edits(source: str) -> Iterable[TextEdit]:
    root = SgRoot(source, "python").root()
    has_import = has_global_import_with_name(root, "typing")

    for applied_operation in make_operations_from_root(root):
        for diagnostic_text_edit in make_diagnostic_text_edits(
            applied_operation=applied_operation, has_import=has_import
        ):
            yield cattrs.structure(diagnostic_text_edit, TextEdit)


def make_quickfix_action(diagnostic: Diagnostic, text_document: TextDocument) -> CodeAction:
    fix = cast(DiagnosticData, diagnostic.data)["fix"]
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
                    edits=[cattrs.structure(edit, TextEdit) for edit in fix["text_edits"]],
                )
            ]
        ),
        diagnostics=[diagnostic],
    )


@LSP_SERVER.feature(INITIALIZE)
def initialize(params: InitializeParams) -> None: ...  # noqa: ARG001


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
@LSP_SERVER.feature(TEXT_DOCUMENT_DID_SAVE)
@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_open_did_save_did_change(
    params: DidOpenTextDocumentParams | DidSaveTextDocumentParams | DidChangeTextDocumentParams,
) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    LSP_SERVER.publish_diagnostics(text_document.uri, diagnostics=list(make_diagnostics(text_document.source)))


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: DidCloseTextDocumentParams) -> None:
    LSP_SERVER.publish_diagnostics(params.text_document.uri, [])


@LSP_SERVER.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(code_action_kinds=[CodeActionKind.QuickFix, CodeActionKind.SourceFixAll], resolve_provider=True),
)
def code_action(params: CodeActionParams) -> list[CodeAction] | None:
    requested_kinds = params.context.only or {CodeActionKind.QuickFix, CodeActionKind.SourceFixAll}
    actions: list[CodeAction] = []

    if CodeActionKind.QuickFix in requested_kinds:
        text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
        actions.extend(
            make_quickfix_action(diagnostic=diagnostic, text_document=text_document)
            for diagnostic in params.context.diagnostics
            if diagnostic.source == LSP_SERVER.name
        )

    if CodeActionKind.SourceFixAll in requested_kinds:
        actions.append(
            CodeAction(
                title=f"{LSP_SERVER.name}: Fix All",
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
                edits=list(make_fixall_text_edits(text_document.source)),
            )
        ],
    )
    return params


def main() -> int:
    LSP_SERVER.start_io()
    return 0
