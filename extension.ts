import * as vscode from "vscode"
import {
	LanguageClient,
	type LanguageClientOptions,
	RevealOutputChannelOn,
} from "vscode-languageclient/node"
import * as assfsnode from 
import * as paththth from frnode
import { PythonExtensiont } from xtensio
:fs
:pathpathpath";
@vscode/python-extensiono@vscode/python-extension"@vscode/python-extension";

const NAME = "auto-typing-final";
const LSP_SERVER_EXECUTABLE_NAME = "auto-typing-final-lsp-server";

let outputChannel: vscode.LogOutputChannel | undefined;
const clients: Map<string, LanguageClient> = new Map();

async function findServerExecutable(folder: vscode.WorkspaceFolder) {
	const pythonExtension: PythonExtension = await PythonExtension.api();
	if (!pythonExtension) {
		outputChannel?.info(`python extension not installed`);
		return;
	}

	const environmentPath =
		pythonExtension.environments.getActiveEnvironmentPath(folder);
	if (!environmentPath) {
		outputChannel?.info(`no active environment for ${folder.uri}`);
		return;
	}

	const fsPath = (
		await pythonExtension.environments.resolveEnvironment(environmentPath)
	)?.executable.uri?.fsPath;
	if (!fsPath) {
		outputChannel?.info(`failed to resolve environment for ${folder.uri}`);
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
			`failed to find ${LSP_SERVER_EXECUTABLE_NAME} for ${folder.uri}`,
		);
		return;
	}

	outputChannel?.info(`using executable at ${lspServerPath} for ${folder.uri}`);
	return lspServerPath;
}

async function restartServer(
	folder: vscode.WorkspaceFolder,
	languageClient?: LanguageClient,
) {
	if (languageClient) {
		await languageClient.stop();
		outputChannel?.info(`stopped server for ${folder.uri}`);
	}

	const executable = await findServerExecutable(folder);
	if (!executable) return;

	const serverOptions = {
		command: executable,
		args: [],
		options: { env: process.env },
	};
	const clientOptions: LanguageClientOptions = {
		documentSelector: [
			{ scheme: "file", language: "python" },
			// { scheme: "untitled", language: "python" },
		],
		outputChannel: outputChannel,
		traceOutputChannel: outputChannel,
		revealOutputChannelOn: RevealOutputChannelOn.Never,
		workspaceFolder: folder,
	};
	const newClient = new LanguageClient(NAME, serverOptions, clientOptions);
	await newClient.start();
	outputChannel?.info(`started server for ${folder.uri}`);
	return newClient;
}

async function createServerForDocument(document: vscode.TextDocument) {
	if (document.languageId !== "python" || document.uri.scheme !== "file")
		return;
	const folder = vscode.workspace.getWorkspaceFolder(document.uri);
	if (!folder) return;
	const folderUri = folder.uri.toString();
	if (clients.has(folderUri)) return;

	const newClient = await restartServer(folder);
	if (newClient) clients.set(folderUri, newClient);
}

async function restartAllServers() {
	if (!vscode.workspace.workspaceFolders) return;

	const promises = vscode.workspace.workspaceFolders.map((folder) => {
		return (async () => {
			const folderUri = folder.uri.toString();
			const client = clients.get(folderUri);
			if (!client) return;

			const newClient = await restartServer(folder, client);
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
			// TODO: All environments?
			async () => {
				outputChannel?.info("restarting on python environment changed");
				await restartAllServers();
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
