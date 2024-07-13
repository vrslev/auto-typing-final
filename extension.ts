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
const CLIENTS: Map<string, LanguageClient> = new Map();
let SORTED_WORKSPACE_FOLDERS: [string, vscode.WorkspaceFolder][] | undefined;

function normalizeFolderUri(workspaceFolder: vscode.WorkspaceFolder) {
	const uri = workspaceFolder.uri.toString();
	return uri.charAt(uri.length - 1) === "/" ? uri : uri + "/";
}

function updateSortedWorkspaceFolders() {
	SORTED_WORKSPACE_FOLDERS = vscode.workspace.workspaceFolders
		?.map<[string, vscode.WorkspaceFolder]>((folder) => [
			normalizeFolderUri(folder),
			folder,
		])
		.sort((first, second) => first[0].length - second[0].length);
}

function getOuterMostWorkspaceFolder(folder: vscode.WorkspaceFolder) {
	const folderUri = normalizeFolderUri(folder);
	for (const [sortedFolderUri, sortedFolder] of SORTED_WORKSPACE_FOLDERS ??
		[]) {
		if (folderUri.startsWith(sortedFolderUri)) return sortedFolder;
	}
	return folder;
}

async function findServerExecutable(workspaceFolder: vscode.WorkspaceFolder) {
	const pythonExtension: PythonExtension = await PythonExtension.api();
	if (!pythonExtension) {
		outputChannel?.info(`python extension not installed`);
		return;
	}

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

async function startClient(workspaceFolder: vscode.WorkspaceFolder) {
	const executable = await findServerExecutable(workspaceFolder);
	if (!executable) return;

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
				// pattern: `${workspaceFolder.uri.fsPath}/**/*`,
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
	CLIENTS.set(workspaceFolder.uri.toString(), languageClient);
	outputChannel?.info(`started server for ${workspaceFolder.uri}`);
}

async function stopClient(workspaceFolder: vscode.WorkspaceFolder) {
	const folderUri = workspaceFolder.uri.toString();
	const oldClient = CLIENTS.get(folderUri);
	if (!oldClient) return;
	await oldClient.stop();
	CLIENTS.delete(folderUri);
	outputChannel?.info(`stopped server for ${folderUri}`);
}

async function restartClientIfAlreadyStarted(
	workspaceFolder: vscode.WorkspaceFolder,
) {
	if (!CLIENTS.has(workspaceFolder.uri.toString())) return;
	await stopClient(workspaceFolder);
	return await startClient(workspaceFolder);
}

async function createServerForDocument(document: vscode.TextDocument) {
	if (document.languageId !== "python" || document.uri.scheme !== "file")
		return;
	let folder = vscode.workspace.getWorkspaceFolder(document.uri);
	if (!folder) return;
	folder = getOuterMostWorkspaceFolder(folder);
	const folderUri = folder.uri.toString();
	if (!CLIENTS.has(folderUri)) await startClient(folder);
}

export async function activate(context: vscode.ExtensionContext) {
	outputChannel = vscode.window.createOutputChannel(EXTENSION_NAME, {
		log: true,
	});
	const pythonExtension: PythonExtension = await PythonExtension.api();

	context.subscriptions.push(
		outputChannel,
		pythonExtension.environments.onDidChangeActiveEnvironmentPath(
			async ({ resource }) => {
				if (!resource) return;
				await restartClientIfAlreadyStarted(
					getOuterMostWorkspaceFolder(resource),
				);
			},
		),
		vscode.commands.registerCommand(`${EXTENSION_NAME}.restart`, async () => {
			outputChannel?.info(`restarting on ${EXTENSION_NAME}.restart`);
			if (!vscode.workspace.workspaceFolders) return;
			await Promise.all(
				vscode.workspace.workspaceFolders
					.map(getOuterMostWorkspaceFolder)
					.map(restartClientIfAlreadyStarted),
			);
		}),
		vscode.workspace.onDidOpenTextDocument(createServerForDocument),
		vscode.workspace.onDidChangeWorkspaceFolders(async ({ removed }) => {
			updateSortedWorkspaceFolders();
			await Promise.all(
				removed.map(getOuterMostWorkspaceFolder).map(stopClient),
			);
		}),
	);

	await Promise.all(
		vscode.workspace.textDocuments.map(createServerForDocument),
	);
}

export async function deactivate() {
	await Promise.all(
		Array.from(CLIENTS.values()).map((client) => client.stop()),
	);
}
