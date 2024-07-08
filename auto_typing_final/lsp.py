import os
import sys
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Final, cast, get_args
from urllib.parse import unquote_to_bytes

import attr
import cattrs
import lsprotocol.types as lsp
from ast_grep_py import SgRoot
from pygls import server

from auto_typing_final.transform import (
    IMPORT_STYLES_TO_IMPORT_CONFIGS,
    AddFinal,
    Edit,
    ImportConfig,
    ImportStyle,
    make_replacements,
)

LSP_SERVER = server.LanguageServer(name="auto-typing-final", version=version("auto-typing-final"), max_workers=5)


@dataclass
class ClientState:
    import_config: ImportConfig
    ignored_paths: list[Path]


STATE = ClientState(import_config=IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"], ignored_paths=[])


# From Python 3.13: https://github.com/python/cpython/blob/0790418a0406cc5419bfd9d718522a749542bbc8/Lib/pathlib/_local.py#L815
def path_from_uri(uri: str) -> Path | None:
    if not uri.startswith("file:"):
        return None
    path = uri[5:]
    if path[:3] == "///":
        # Remove empty authority
        path = path[2:]
    elif path[:12] == "//localhost/":
        # Remove 'localhost' authority
        path = path[11:]
    if path[:3] == "///" or (path[:1] == "/" and path[2:3] in ":|"):
        # Remove slash before DOS device/UNC path
        path = path[1:]
    if path[1:2] == "|":
        # Replace bar with colon in DOS drive
        path = path[:1] + ":" + path[2:]

    path_: Final = Path(os.fsdecode(unquote_to_bytes(path)))
    if not path_.is_absolute():
        return None
    return path_


@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(_: lsp.InitializeParams) -> None:
    executable_path: Final = Path(sys.executable)

    if executable_path.parent.name == "bin":
        STATE.ignored_paths = [executable_path.parent.parent]


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
        STATE.import_config = IMPORT_STYLES_TO_IMPORT_CONFIGS[import_style]


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
    result: Final = make_replacements(root=SgRoot(source, "python").root(), import_config=STATE.import_config)

    for replacement in result.replacements:
        if replacement.operation_type == AddFinal:
            fix_message = f"{LSP_SERVER.name}: Add {STATE.import_config.value}"
            diagnostic_message = f"Missing {STATE.import_config.value}"
        else:
            fix_message = f"{LSP_SERVER.name}: Remove {STATE.import_config.value}"
            diagnostic_message = f"Unexpected {STATE.import_config.value}"

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
    result: Final = make_replacements(root=SgRoot(source, "python").root(), import_config=STATE.import_config)

    for replacement in result.replacements:
        for edit in replacement.edits:
            yield make_text_edit(edit)

    if result.import_text:
        yield make_import_text_edit(result.import_text)


def path_is_ignored(uri: str) -> bool:
    if path := path_from_uri(uri):
        return any(path.is_relative_to(ignored_path) for ignored_path in STATE.ignored_paths)
    return False


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_open_did_save_did_change(
    params: lsp.DidOpenTextDocumentParams | lsp.DidSaveTextDocumentParams | lsp.DidChangeTextDocumentParams,
) -> None:
    if path_is_ignored(params.text_document.uri):
        return
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
