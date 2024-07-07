import uuid
from collections.abc import Iterable
from importlib.metadata import version
from typing import Final, cast, get_args

import attr
import cattrs
import lsprotocol.types as lsp
from ast_grep_py import SgRoot
from pygls import server
from pygls.workspace import TextDocument

from auto_typing_final.transform import (
    IMPORT_STYLES_TO_IMPORT_CONFIGS,
    AddFinal,
    Edit,
    ImportConfig,
    ImportStyle,
    make_replacements,
)

LSP_SERVER = server.LanguageServer(name="auto-typing-final", version=version("auto-typing-final"), max_workers=5)
IMPORT_CONFIG: ImportConfig | None = None


@attr.define
class Fix:
    message: str
    text_edits: list[lsp.TextEdit]


@attr.define
class DiagnosticData:
    fix: Fix


def make_import_text_edit(import_text: str) -> lsp.TextEdit:
    return lsp.TextEdit(
        range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=0)),
        new_text=f"{import_text}\n",
    )


def make_text_edit(edit: Edit) -> lsp.TextEdit:
    node_range: Final = edit.node.range()
    return lsp.TextEdit(
        range=lsp.Range(
            start=lsp.Position(line=node_range.start.line, character=node_range.start.column),
            end=lsp.Position(line=node_range.end.line, character=node_range.end.column),
        ),
        new_text=edit.new_text,
    )


def make_diagnostics(source: str) -> Iterable[lsp.Diagnostic]:
    if not IMPORT_CONFIG:
        return
    result: Final = make_replacements(root=SgRoot(source, "python").root(), import_config=IMPORT_CONFIG)

    for replacement in result.replacements:
        if replacement.operation_type == AddFinal:
            fix_message = f"{LSP_SERVER.name}: Add {IMPORT_CONFIG.value}"
            diagnostic_message = f"Missing {IMPORT_CONFIG.value}"
        else:
            fix_message = f"{LSP_SERVER.name}: Remove {IMPORT_CONFIG.value}"
            diagnostic_message = f"Unexpected {IMPORT_CONFIG.value}"

        fix = Fix(message=fix_message, text_edits=[make_text_edit(edit) for edit in replacement.edits])
        if result.import_text:
            fix.text_edits.append(make_import_text_edit(result.import_text))

        for applied_edit in replacement.edits:
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
    if not IMPORT_CONFIG:
        return
    result: Final = make_replacements(root=SgRoot(source, "python").root(), import_config=IMPORT_CONFIG)

    for replacement in result.replacements:
        for edit in replacement.edits:
            yield make_text_edit(edit)

    if result.import_text:
        yield make_import_text_edit(result.import_text)


def make_workspace_edit(text_document: TextDocument, text_edits: list[lsp.TextEdit]) -> lsp.WorkspaceEdit:
    return lsp.WorkspaceEdit(
        document_changes=[
            lsp.TextDocumentEdit(
                text_document=lsp.OptionalVersionedTextDocumentIdentifier(
                    uri=text_document.uri, version=text_document.version
                ),
                edits=text_edits,  # type: ignore[arg-type]
            )
        ]
    )


@LSP_SERVER.feature(lsp.INITIALIZE)
async def initialize(_: lsp.InitializeParams) -> None: ...


@LSP_SERVER.feature(lsp.INITIALIZED)
async def initialized(_: lsp.InitializedParams) -> None:
    await LSP_SERVER.register_capability_async(
        params=lsp.RegistrationParams(
            registrations=[
                lsp.Registration(
                    id=str(uuid.uuid4()),
                    method=lsp.WORKSPACE_DID_CHANGE_CONFIGURATION,
                    register_options=lsp.DidChangeConfigurationRegistrationOptions(section=LSP_SERVER.name),
                )
            ]
        )
    )


@LSP_SERVER.feature(lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
def workspace_did_change_configuration(params: lsp.DidChangeConfigurationParams) -> None:
    if (
        isinstance(params.settings, dict)
        and (settings := params.settings.get(LSP_SERVER.name))
        and isinstance(settings, dict)
        and (import_style := settings.get("import-style"))
        and (import_style in get_args(ImportStyle))
    ):
        global IMPORT_CONFIG  # noqa: PLW0603
        IMPORT_CONFIG = IMPORT_STYLES_TO_IMPORT_CONFIGS[import_style]


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_open_did_save_did_change(
    params: lsp.DidOpenTextDocumentParams | lsp.DidSaveTextDocumentParams | lsp.DidChangeTextDocumentParams,
) -> None:
    text_document: Final = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
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
    requested_kinds: Final = params.context.only or {lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.SourceFixAll}
    actions: Final[list[lsp.CodeAction]] = []

    if lsp.CodeActionKind.QuickFix in requested_kinds:
        text_document: Final = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
        our_diagnostics: Final = [
            diagnostic for diagnostic in params.context.diagnostics if diagnostic.source == LSP_SERVER.name
        ]

        for diagnostic in our_diagnostics:
            data = cattrs.structure(diagnostic.data, DiagnosticData)
            actions.append(
                lsp.CodeAction(
                    title=data.fix.message,
                    kind=lsp.CodeActionKind.QuickFix,
                    edit=make_workspace_edit(text_document=text_document, text_edits=data.fix.text_edits),
                    diagnostics=[diagnostic],
                )
            )

        if our_diagnostics:
            actions.append(
                lsp.CodeAction(
                    title=f"{LSP_SERVER.name}: Fix All",
                    kind=lsp.CodeActionKind.QuickFix,
                    data=params.text_document.uri,
                    edit=None,
                    diagnostics=params.context.diagnostics,
                )
            )

    if lsp.CodeActionKind.SourceFixAll in requested_kinds:
        actions.append(
            lsp.CodeAction(
                title=f"{LSP_SERVER.name}: Fix All",
                kind=lsp.CodeActionKind.SourceFixAll,
                data=params.text_document.uri,
                edit=None,
                diagnostics=params.context.diagnostics,
            ),
        )

    return actions or None


@LSP_SERVER.feature(lsp.CODE_ACTION_RESOLVE)
def resolve_code_action(params: lsp.CodeAction) -> lsp.CodeAction:
    text_document: Final = LSP_SERVER.workspace.get_text_document(cast(str, params.data))
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
