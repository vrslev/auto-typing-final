from collections.abc import Iterable
from typing import cast

import attr
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
    DiagnosticSeverity,
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


@attr.define
class Fix:
    message: str
    text_edits: list[TextEdit]


@attr.define
class DiagnosticData:
    fix: Fix


def make_typing_import() -> TextEdit:
    return TextEdit(
        range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
        new_text="import typing\n",
    )


def make_diagnostic_text_edits(applied_operation: AppliedOperation) -> Iterable[TextEdit]:
    for edit in applied_operation.edits:
        node_range = edit.node.range()
        yield TextEdit(
            range=Range(
                start=Position(line=node_range.start.line, character=node_range.start.column),
                end=Position(line=node_range.end.line, character=node_range.end.column),
            ),
            new_text=edit.edit.inserted_text,
        )


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

        fix = Fix(
            message=fix_message,
            text_edits=list(make_diagnostic_text_edits(applied_operation=applied_operation)),
        )

        if isinstance(applied_operation.operation, AddFinal) and not has_import:
            fix.text_edits.append(make_typing_import())

        for applied_edit in applied_operation.edits:
            node_range = applied_edit.node.range()
            yield Diagnostic(
                range=Range(
                    start=Position(line=node_range.start.line, character=node_range.start.column),
                    end=Position(line=node_range.end.line, character=node_range.end.column),
                ),
                message=diagnostic_message,
                severity=DiagnosticSeverity.Warning,
                source=LSP_SERVER.name,
                data=cattrs.unstructure(DiagnosticData(fix=fix)),
            )


def make_fixall_text_edits(source: str) -> Iterable[TextEdit]:
    root = SgRoot(source, "python").root()
    has_import = has_global_import_with_name(root, "typing")
    has_add_final_operation = False

    for applied_operation in make_operations_from_root(root):
        if isinstance(applied_operation.operation, AddFinal):
            has_add_final_operation = True
        yield from make_diagnostic_text_edits(applied_operation)

    if has_add_final_operation and not has_import:
        yield make_typing_import()


def make_quickfix_action(diagnostic: Diagnostic, text_document: TextDocument) -> CodeAction:
    data = cattrs.structure(diagnostic.data, DiagnosticData)
    return CodeAction(
        title=data.fix.message,
        kind=CodeActionKind.QuickFix,
        data=text_document.uri,
        edit=WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    text_document=OptionalVersionedTextDocumentIdentifier(
                        uri=text_document.uri, version=text_document.version
                    ),
                    edits=data.fix.text_edits,  # type: ignore[arg-type]
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
