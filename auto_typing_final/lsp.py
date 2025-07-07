import os
import sys
import uuid
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any, Final, TypedDict, cast
from urllib.parse import unquote_to_bytes

import attr
import cattrs
import lsprotocol.types as lsp
from ast_grep_py import SgRoot
from pygls.server import LanguageServer

from auto_typing_final.transform import (
    IMPORT_STYLES_TO_IMPORT_CONFIGS,
    AddFinal,
    Edit,
    ImportConfig,
    ImportStyle,
    make_replacements,
)


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


ClientSettings = TypedDict("ClientSettings", {"import-style": ImportStyle})
FullClientSettings = TypedDict("FullClientSettings", {"auto-typing-final": ClientSettings})


@attr.define
class Fix:
    message: str
    text_edits: list[lsp.TextEdit | lsp.AnnotatedTextEdit]


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


@dataclass(frozen=True, slots=True, kw_only=True)
class Service:
    ls_name: str
    ignored_paths: list[Path]
    import_config: ImportConfig

    @staticmethod
    def try_from_settings(ls_name: str, settings: Any) -> "Service | None":  # noqa: ANN401
        try:
            validated_settings: Final = cattrs.structure(settings, FullClientSettings)
        except cattrs.BaseValidationError:
            return None

        executable_path: Final = Path(sys.executable)
        return Service(
            ls_name=ls_name,
            ignored_paths=[executable_path.parent.parent] if executable_path.parent.name == "bin" else [],
            import_config=IMPORT_STYLES_TO_IMPORT_CONFIGS[validated_settings["auto-typing-final"]["import-style"]],
        )

    def make_diagnostics(self, source: str) -> list[lsp.Diagnostic]:
        replacement_result: Final = make_replacements(
            root=SgRoot(source, "python").root(), import_config=self.import_config
        )
        result: Final = []

        for replacement in replacement_result.replacements:
            if replacement.operation_type == AddFinal:
                fix_message = f"{self.ls_name}: Add {self.import_config.value}"
                diagnostic_message = f"Missing {self.import_config.value}"
            else:
                fix_message = f"{self.ls_name}: Remove {self.import_config.value}"
                diagnostic_message = f"Unexpected {self.import_config.value}"

            fix = Fix(message=fix_message, text_edits=[make_text_edit(edit) for edit in replacement.edits])
            if replacement_result.import_text:
                fix.text_edits.append(make_import_text_edit(replacement_result.import_text))

            for applied_edit in replacement.edits:
                node_range = applied_edit.node.range()
                result.append(
                    lsp.Diagnostic(
                        range=lsp.Range(
                            start=lsp.Position(line=node_range.start.line, character=node_range.start.column),
                            end=lsp.Position(line=node_range.end.line, character=node_range.end.column),
                        ),
                        message=diagnostic_message,
                        severity=lsp.DiagnosticSeverity.Warning,
                        source=self.ls_name,
                        data=cattrs.unstructure(fix),
                    )
                )
        return result

    def make_fix_all_text_edits(self, source: str) -> list[lsp.TextEdit | lsp.AnnotatedTextEdit]:
        replacement_result: Final = make_replacements(
            root=SgRoot(source, "python").root(), import_config=self.import_config
        )
        result: Final[list[lsp.TextEdit | lsp.AnnotatedTextEdit]] = [
            make_text_edit(edit) for replacement in replacement_result.replacements for edit in replacement.edits
        ]
        if replacement_result.import_text:
            result.append(make_import_text_edit(replacement_result.import_text))
        return result

    def path_is_ignored(self, uri: str) -> bool:
        if path := path_from_uri(uri):
            return any(path.is_relative_to(ignored_path) for ignored_path in self.ignored_paths)
        return False


class CustomLanguageServer(LanguageServer):
    service: Service | None = None


LSP_SERVER = CustomLanguageServer(name="auto-typing-final", version=version("auto-typing-final"), max_workers=5)


@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(_: lsp.InitializeParams) -> None: ...


@LSP_SERVER.feature(lsp.INITIALIZED)
async def initialized(ls: CustomLanguageServer, _: lsp.InitializedParams) -> None:
    await ls.register_capability_async(
        params=lsp.RegistrationParams(
            registrations=[
                lsp.Registration(
                    id=str(uuid.uuid4()),
                    method=lsp.WORKSPACE_DID_CHANGE_CONFIGURATION,
                    register_options=lsp.DidChangeConfigurationRegistrationOptions(section=ls.name),
                ),
            ]
        )
    )


@LSP_SERVER.feature(lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
def workspace_did_change_configuration(ls: CustomLanguageServer, params: lsp.DidChangeConfigurationParams) -> None:
    ls.service = Service.try_from_settings(ls_name=ls.name, settings=params.settings) or ls.service
    if not ls.service:
        return
    for text_document in ls.workspace.text_documents.values():
        ls.publish_diagnostics(text_document.uri, diagnostics=ls.service.make_diagnostics(text_document.source))


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_open_did_save_did_change(
    ls: CustomLanguageServer,
    params: lsp.DidOpenTextDocumentParams | lsp.DidSaveTextDocumentParams | lsp.DidChangeTextDocumentParams,
) -> None:
    if not ls.service:
        return
    if ls.service.path_is_ignored(params.text_document.uri):
        return
    text_document: Final = ls.workspace.get_text_document(params.text_document.uri)
    ls.publish_diagnostics(text_document.uri, diagnostics=ls.service.make_diagnostics(text_document.source))


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: CustomLanguageServer, params: lsp.DidCloseTextDocumentParams) -> None:
    ls.publish_diagnostics(params.text_document.uri, [])


@LSP_SERVER.feature(
    lsp.TEXT_DOCUMENT_CODE_ACTION,
    lsp.CodeActionOptions(
        code_action_kinds=[lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.SourceFixAll], resolve_provider=True
    ),
)
def code_action(ls: CustomLanguageServer, params: lsp.CodeActionParams) -> list[lsp.CodeAction] | None:
    requested_kinds: Final = params.context.only or {lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.SourceFixAll}
    actions: Final[list[lsp.CodeAction]] = []

    if lsp.CodeActionKind.QuickFix in requested_kinds:
        text_document: Final = ls.workspace.get_text_document(params.text_document.uri)
        our_diagnostics: Final = [
            diagnostic for diagnostic in params.context.diagnostics if diagnostic.source == ls.name
        ]

        for diagnostic in our_diagnostics:
            fix = cattrs.structure(diagnostic.data, Fix)
            actions.append(
                lsp.CodeAction(
                    title=fix.message,
                    kind=lsp.CodeActionKind.QuickFix,
                    edit=lsp.WorkspaceEdit(
                        document_changes=[
                            lsp.TextDocumentEdit(
                                text_document=lsp.OptionalVersionedTextDocumentIdentifier(
                                    uri=text_document.uri, version=text_document.version
                                ),
                                edits=fix.text_edits,
                            )
                        ]
                    ),
                    diagnostics=[diagnostic],
                )
            )

        if our_diagnostics:
            actions.append(
                lsp.CodeAction(
                    title=f"{ls.name}: Fix All",
                    kind=lsp.CodeActionKind.QuickFix,
                    data=params.text_document.uri,
                    edit=None,
                    diagnostics=params.context.diagnostics,
                )
            )

    if lsp.CodeActionKind.SourceFixAll in requested_kinds:
        actions.append(
            lsp.CodeAction(
                title=f"{ls.name}: Fix All",
                kind=lsp.CodeActionKind.SourceFixAll,
                data=params.text_document.uri,
                diagnostics=params.context.diagnostics,
            ),
        )

    return actions or None


@LSP_SERVER.feature(lsp.CODE_ACTION_RESOLVE)
def resolve_code_action(ls: CustomLanguageServer, params: lsp.CodeAction) -> lsp.CodeAction:
    if ls.service:
        text_document: Final = ls.workspace.get_text_document(cast(str, params.data))
        params.edit = lsp.WorkspaceEdit(
            document_changes=[
                lsp.TextDocumentEdit(
                    text_document=lsp.OptionalVersionedTextDocumentIdentifier(
                        uri=text_document.uri, version=text_document.version
                    ),
                    edits=ls.service.make_fix_all_text_edits(text_document.source),
                )
            ],
        )
    return params


def main() -> int:
    LSP_SERVER.start_io()
    return 0
