from collections.abc import Iterable
from importlib.metadata import version
from typing import cast

import attr
import cattrs
import lsprotocol.types as lsp
from ast_grep_py import SgRoot
from pygls import server
from pygls.workspace import TextDocument

from auto_typing_final.finder import has_global_import_with_name
from auto_typing_final.transform import AddFinal, AppliedOperation, make_operations_from_root

LSP_SERVER = server.LanguageServer(name="auto-typing-final", version=version("auto-typing-final"), max_workers=5)


@attr.define
class Fix:
    message: str
    text_edits: list[lsp.TextEdit]


@attr.define
class DiagnosticData:
    fix: Fix


def make_typing_import() -> lsp.TextEdit:
    return lsp.TextEdit(
        range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=0)),
        new_text="import typing\n",
    )


def make_diagnostic_text_edits(applied_operation: AppliedOperation) -> Iterable[lsp.TextEdit]:
    for applied_edit in applied_operation.edits:
        node_range = applied_edit.node.range()
        yield lsp.TextEdit(
            range=lsp.Range(
                start=lsp.Position(line=node_range.start.line, character=node_range.start.column),
                end=lsp.Position(line=node_range.end.line, character=node_range.end.column),
            ),
            new_text=applied_edit.edit.inserted_text,
        )


def make_diagnostics(source: str) -> Iterable[lsp.Diagnostic]:
    root = SgRoot(source, "python").root()
    has_import = has_global_import_with_name(root, "typing")

    for applied_operation in make_operations_from_root(root):
        if isinstance(applied_operation.operation, AddFinal):
            fix_message = f"{LSP_SERVER.name}: Add typing.Final"
            diagnostic_message = "Missing typing.Final"
        else:
            fix_message = f"{LSP_SERVER.name}: Remove typing.Final"
            diagnostic_message = "Unexpected typing.Final"

        fix = Fix(message=fix_message, text_edits=list(make_diagnostic_text_edits(applied_operation)))

        if isinstance(applied_operation.operation, AddFinal) and not has_import:
            fix.text_edits.append(make_typing_import())

        for applied_edit in applied_operation.edits:
            node_range = applied_edit.node.range()
            yield lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=node_range.start.line, character=node_range.start.column),
                    end=lsp.Position(line=node_range.end.line, character=node_range.end.column),
                ),
                message=diagnostic_message,
                severity=lsp.DiagnosticSeverity.Warning,
                source=LSP_SERVER.name,
                data=cattrs.unstructure(DiagnosticData(fix=fix)),
            )


def make_fixall_text_edits(source: str) -> Iterable[lsp.TextEdit]:
    root = SgRoot(source, "python").root()
    has_import = has_global_import_with_name(root, "typing")
    has_add_final_operation = False

    for applied_operation in make_operations_from_root(root):
        if isinstance(applied_operation.operation, AddFinal):
            has_add_final_operation = True
        yield from make_diagnostic_text_edits(applied_operation)

    if has_add_final_operation and not has_import:
        yield make_typing_import()


def make_quickfix_action(diagnostic: lsp.Diagnostic, text_document: TextDocument) -> lsp.CodeAction:
    data = cattrs.structure(diagnostic.data, DiagnosticData)
    return lsp.CodeAction(
        title=data.fix.message,
        kind=lsp.CodeActionKind.QuickFix,
        data=text_document.uri,
        edit=lsp.WorkspaceEdit(
            document_changes=[
                lsp.TextDocumentEdit(
                    text_document=lsp.OptionalVersionedTextDocumentIdentifier(
                        uri=text_document.uri, version=text_document.version
                    ),
                    edits=data.fix.text_edits,  # type: ignore[arg-type]
                )
            ]
        ),
        diagnostics=[diagnostic],
    )


@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(params: lsp.InitializeParams) -> None: ...  # noqa: ARG001


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_open_did_save_did_change(
    params: lsp.DidOpenTextDocumentParams | lsp.DidSaveTextDocumentParams | lsp.DidChangeTextDocumentParams,
) -> None:
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    LSP_SERVER.publish_diagnostics(text_document.uri, diagnostics=list(make_diagnostics(text_document.source)))


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
    LSP_SERVER.publish_diagnostics(params.text_document.uri, [])


@LSP_SERVER.feature(
    lsp.TEXT_DOCUMENT_CODE_ACTION,
    lsp.CodeActionOptions(
        code_action_kinds=[lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.SourceFixAll], resolve_provider=True
    ),
)
def code_action(params: lsp.CodeActionParams) -> list[lsp.CodeAction] | None:
    requested_kinds = params.context.only or {lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.SourceFixAll}
    actions: list[lsp.CodeAction] = []

    if lsp.CodeActionKind.QuickFix in requested_kinds:
        text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
        actions.extend(
            make_quickfix_action(diagnostic=diagnostic, text_document=text_document)
            for diagnostic in params.context.diagnostics
            if diagnostic.source == LSP_SERVER.name
        )

    if lsp.CodeActionKind.SourceFixAll in requested_kinds:
        actions.append(
            lsp.CodeAction(
                title=f"{LSP_SERVER.name}: Fix All",
                kind=lsp.CodeActionKind.SourceFixAll,
                data=params.text_document.uri,
                edit=None,
                diagnostics=[],
            ),
        )

    return actions or None


@LSP_SERVER.feature(lsp.CODE_ACTION_RESOLVE)
def resolve_code_action(params: lsp.CodeAction) -> lsp.CodeAction:
    if params.kind != lsp.CodeActionKind.SourceFixAll:
        return params

    text_document = LSP_SERVER.workspace.get_text_document(cast(str, params.data))
    params.edit = lsp.WorkspaceEdit(
        document_changes=[
            lsp.TextDocumentEdit(
                text_document=lsp.OptionalVersionedTextDocumentIdentifier(
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
