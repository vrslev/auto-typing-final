import { PythonExtension } from "@vscode/python-extension";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import {
	LanguageClient,
	type LanguageClientOptions,
	RevealOutputChannelOn,
} from "vscode-languageclient/node";

const NAME = "auto-typing-final";
const LSP_SERVER_EXECUTABLE_NAME = "auto-typing-final-lsp-server";

let outputChannel: vscode.LogOutputChannel | undefined;
const clients: Map<string, LanguageClient> = new Map();

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
		documentSelector: [{ scheme: "file", language: "python" }],
		outputChannel: outputChannel,
		traceOutputChannel: outputChannel,
		revealOutputChannelOn: RevealOutputChannelOn.Never,
		workspaceFolder: workspaceFolder,
	};
	const languageClient = new LanguageClient(NAME, serverOptions, clientOptions);
	await languageClient.start();
	outputChannel?.info(`started server for ${workspaceFolder.uri}`);
	return languageClient;
}

async function restartClient(
	workspaceFolder: vscode.WorkspaceFolder,
	languageClient: LanguageClient,
) {
	await languageClient.stop();
	outputChannel?.info(`stopped server for ${workspaceFolder.uri}`);
	return await startClient(workspaceFolder);
}

async function createServerForDocument(document: vscode.TextDocument) {
	if (document.languageId !== "python" || document.uri.scheme !== "file")
		return;
	const folder = vscode.workspace.getWorkspaceFolder(document.uri);
	if (!folder) return;
	const folderUri = folder.uri.toString();
	if (clients.has(folderUri)) return;

	const newClient = await startClient(folder);
	if (newClient) clients.set(folderUri, newClient);
}

async function restartAllServers() {
	if (!vscode.workspace.workspaceFolders) return;

	const promises = vscode.workspace.workspaceFolders.map((folder) => {
		return (async () => {
			const folderUri = folder.uri.toString();
			const client = clients.get(folderUri);
			if (!client) return;

			const newClient = await restartClient(folder, client);
			if (newClient) {
				clients.set(folderUri, newClient);
			} else {
				clients.delete(folderUri);
			}
		})();
	});
	await Promise.all(promises);
}

export async function activate(context: vscode.ExtensionContext) {
	outputChannel = vscode.window.createOutputChannel(NAME, { log: true });

	const pythonExtension: PythonExtension = await PythonExtension.api();

	context.subscriptions.push(
		outputChannel,
		pythonExtension.environments.onDidChangeActiveEnvironmentPath(
			async (event) => {
				const folder = event.resource;
				if (!folder) return;
				const folderUri = folder.uri.toString();

				const client = clients.get(folderUri);
				if (!client) return;

				const newClient = await restartClient(folder, client);
				if (newClient) {
					clients.set(folderUri, newClient);
				} else {
					clients.delete(folderUri);
				}
			},
		),
		vscode.commands.registerCommand(`${NAME}.restart`, async () => {
			outputChannel?.info(`restarting on ${NAME}.restart`);
			await restartAllServers();
		}),
		vscode.workspace.onDidOpenTextDocument(createServerForDocument),
		vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
			const promises = event.removed.map((folder) => {
				return (async () => {
					const folderUri = folder.uri.toString();
					const client = clients.get(folderUri);
					if (client) {
						outputChannel?.info(`stopping server for ${folder.uri}`);
						await client.stop();
						clients.delete(folderUri);
					}
				})();
			});
			await Promise.all(promises);
		}),
	);

	await Promise.all(
		vscode.workspace.textDocuments.map(createServerForDocument),
	);
}

export async function deactivate() {
	const promises = [];
	for (const client of clients.values()) {
		promises.push(client.stop());
	}
	await Promise.all(promises);
}
