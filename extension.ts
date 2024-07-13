import { PythonExtension } from "@vscode/python-extension";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import {
	LanguageClient,
	type LanguageClientOptions,
	RevealOutputChannelOn,
} from "vscode-languageclient/node";

const EXTENSION_NAME = "auto-typing-final";
const LSP_SERVER_EXECUTABLE_NAME = "auto-typing-final-lsp-server";
let outputChannel: vscode.LogOutputChannel | undefined;

function normalizeFolderUri(workspaceFolder: vscode.WorkspaceFolder) {
	const uri = workspaceFolder.uri.toString();
	return uri.charAt(uri.length - 1) === "/" ? uri : uri + "/";
}

function getSortedWorkspaceFolders() {
	return vscode.workspace.workspaceFolders
		?.map<[string, vscode.WorkspaceFolder]>((folder) => [
			normalizeFolderUri(folder),
			folder,
		])
		.sort((first, second) => first[0].length - second[0].length);
}
let SORTED_WORKSPACE_FOLDERS = getSortedWorkspaceFolders();
function getOuterMostWorkspaceFolder(folder: vscode.WorkspaceFolder) {
	const folderUri = normalizeFolderUri(folder);
	for (const [sortedFolderUri, sortedFolder] of SORTED_WORKSPACE_FOLDERS ??
		[]) {
		if (folderUri.startsWith(sortedFolderUri)) return sortedFolder;
	}
	return folder;
}

async function getPythonExtension() {
	try {
		return await PythonExtension.api();
	} catch {
		outputChannel?.info(`python extension not installed`);
		return;
	}
}

async function findServerExecutable(workspaceFolder: vscode.WorkspaceFolder) {
	const pythonExtension = await getPythonExtension();
	if (!pythonExtension) return;

	const environmentPath =
		pythonExtension.environments.getActiveEnvironmentPath(workspaceFolder);
	if (!environmentPath) {
		outputChannel?.info(`no active environment for ${workspaceFolder.uri}`);
		return;
	}

	const fsPath = (
		await pythonExtension.environments.resolveEnvironment(environmentPath)
	)?.executable.uri?.fsPath;
	if (!fsPath) {
		outputChannel?.info(
			`failed to resolve environment for ${workspaceFolder.uri}`,
		);
		return;
	}

	const parsedPath = path.parse(fsPath);
	const lspServerPath = path.format({
		base: LSP_SERVER_EXECUTABLE_NAME,
		dir: parsedPath.dir,
		root: parsedPath.root,
	});
	if (!fs.existsSync(lspServerPath)) {
		outputChannel?.info(
			`failed to find ${LSP_SERVER_EXECUTABLE_NAME} for ${workspaceFolder.uri}`,
		);
		return;
	}

	outputChannel?.info(
		`using executable at ${lspServerPath} for ${workspaceFolder.uri}`,
	);
	return lspServerPath;
}

async function createClient(
	workspaceFolder: vscode.WorkspaceFolder,
	executable: string,
) {
	const serverOptions = {
		command: executable,
		args: [],
		options: { env: process.env },
	};
	const clientOptions: LanguageClientOptions = {
		documentSelector: [
			{
				scheme: "file",
				language: "python",
				pattern: `${workspaceFolder.uri.fsPath}/**/*`,
			},
		],
		outputChannel: outputChannel,
		traceOutputChannel: outputChannel,
		revealOutputChannelOn: RevealOutputChannelOn.Never,
		workspaceFolder: workspaceFolder,
	};
	const languageClient = new LanguageClient(
		EXTENSION_NAME,
		serverOptions,
		clientOptions,
	);
	await languageClient.start();
	outputChannel?.info(`started server for ${workspaceFolder.uri}`);
	return languageClient;
}

function createClientManager() {
	const allClients: Map<string, [string, LanguageClient]> = new Map();

	async function _stopClient(workspaceFolder: vscode.WorkspaceFolder) {
		const folderUri = workspaceFolder.uri.toString();
		const oldEntry = allClients.get(folderUri);
		if (oldEntry) {
			const [_, oldClient] = oldEntry;
			await oldClient.stop();
			allClients.delete(folderUri);
			outputChannel?.info(`stopped server for ${folderUri}`);
		}
	}

	async function requireClientForWorkspace(
		workspaceFolder: vscode.WorkspaceFolder,
	) {
		const outerMostFolder = getOuterMostWorkspaceFolder(workspaceFolder);
		const outerMostFolderUri = outerMostFolder.uri.toString();

		if (workspaceFolder.uri.toString() != outerMostFolderUri) {
			await _stopClient(workspaceFolder);
		}

		const outerMostOldEntry = allClients.get(outerMostFolderUri);
		const newExecutable = await findServerExecutable(outerMostFolder);

		if (outerMostOldEntry) {
			const [oldExecutable, _] = outerMostOldEntry;
			if (oldExecutable == newExecutable) {
				return;
			}
			await _stopClient(outerMostFolder);
		}

		if (newExecutable) {
			allClients.set(outerMostFolderUri, [
				newExecutable,
				await createClient(outerMostFolder, newExecutable),
			]);
		}
	}
	return {
		requireClientForWorkspace,
		async requireClientsForWorkspaces(
			workspaceFolders: readonly vscode.WorkspaceFolder[],
		) {
			const outerMostFolders = [
				...new Set(workspaceFolders.map(getOuterMostWorkspaceFolder)),
			];
			await Promise.all(
				outerMostFolders.map((folder) => requireClientForWorkspace(folder)),
			);
		},
		async stopClientsForWorkspaces(
			workspaceFolders: readonly vscode.WorkspaceFolder[],
		) {
			await Promise.all(
				workspaceFolders.map(async (folder) => {
					const outerMostFolder = getOuterMostWorkspaceFolder(folder);
					if (outerMostFolder.uri.toString() === folder.uri.toString()) {
						await _stopClient(folder);
					}
				}),
			);
		},
		async stopAllClients() {
			await Promise.all(
				Array.from(allClients.values()).map(([_, client]) => client.stop()),
			);
		},
	};
}

export async function activate(context: vscode.ExtensionContext) {
	outputChannel = vscode.window.createOutputChannel(EXTENSION_NAME, {
		log: true,
	});
	const clientManager = createClientManager();

	function getWorkspaceFolderFromDocument(document: vscode.TextDocument) {
		if (document.languageId !== "python" || document.uri.scheme !== "file")
			return;

		return vscode.workspace.getWorkspaceFolder(document.uri);
	}

	context.subscriptions.push(
		outputChannel,
		(await getPythonExtension())?.environments.onDidChangeActiveEnvironmentPath(
			async ({ resource }) => {
				if (!resource) return;
				await clientManager.requireClientForWorkspace(resource);
			},
		) || { dispose: () => undefined },
		vscode.commands.registerCommand(`${EXTENSION_NAME}.restart`, async () => {
			if (!vscode.workspace.workspaceFolders) return;
			outputChannel?.info(`restarting on ${EXTENSION_NAME}.restart`);
			await clientManager.stopAllClients();
			await clientManager.requireClientsForWorkspaces(
				vscode.workspace.workspaceFolders,
			);
		}),
		vscode.workspace.onDidOpenTextDocument(async (document) => {
			const folder = getWorkspaceFolderFromDocument(document);
			if (folder) {
				await clientManager.requireClientForWorkspace(folder);
			}
		}),
		vscode.workspace.onDidChangeWorkspaceFolders(async ({ removed }) => {
			SORTED_WORKSPACE_FOLDERS = getSortedWorkspaceFolders();
			await clientManager.stopClientsForWorkspaces(removed);
		}),
		{ dispose: clientManager.stopAllClients },
	);

	await clientManager.requireClientsForWorkspaces(
		vscode.workspace.textDocuments
			.map(getWorkspaceFolderFromDocument)
			.filter((value) => value !== undefined),
	);
}
