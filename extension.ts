import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import {
	LanguageClient,
	type LanguageClientOptions,
	RevealOutputChannelOn,
} from "vscode-languageclient/node";

const NAME = "auto-typing-final";
const PYTHON_EXTENSION_ID = "ms-python.python";
const LSP_SERVER_EXECUTABLE_NAME = "auto-typing-final-lsp-server";

let outputChannel: vscode.LogOutputChannel | undefined;
const clients: Map<string, LanguageClient> = new Map();

function getPythonExtension() {
	return vscode.extensions.getExtension(PYTHON_EXTENSION_ID) as
		| vscode.Extension<{
				environments: {
					onDidChangeActiveEnvironmentPath: (event: any) => any;
					getActiveEnvironmentPath: () => { path: string };
					resolveEnvironment: (environment: { path: string }) => Promise<
						{ executable: { uri?: { fsPath: string } } } | undefined
					>;
				};
		  }>
		| undefined;
}

async function findServerExecutable() {
	const extension = getPythonExtension();
	if (!extension) {
		outputChannel?.info(`${PYTHON_EXTENSION_ID} not installed`);
		return;
	}

	const environmentPath =
		extension.exports.environments.getActiveEnvironmentPath();
	if (!environmentPath) {
		outputChannel?.info(`no active environment`);
		return;
	}

	const fsPath = (
		await extension.exports.environments.resolveEnvironment(environmentPath)
	)?.executable.uri?.fsPath;
	if (!fsPath) {
		outputChannel?.info(`failed to resolve environment at ${environmentPath}`);
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
			`failed to find ${LSP_SERVER_EXECUTABLE_NAME} for ${fsPath}`,
		);
		return;
	}

	outputChannel?.info(`using executable at ${lspServerPath}`);
	return lspServerPath;
}

async function restartServer(languageClient?: LanguageClient) {
	if (languageClient) {
		await languageClient.stop();
		outputChannel?.info("stopped server");
	}

	const executable = await findServerExecutable();
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
	};
	const newClient = new LanguageClient(NAME, serverOptions, clientOptions);
	await newClient.start();
	outputChannel?.info("started server");
	return newClient;
}

async function createServerForDocument(document: vscode.TextDocument) {
	if (document.languageId !== "python" || document.uri.scheme !== "file")
		return;
	const folder = vscode.workspace.getWorkspaceFolder(document.uri);
	if (!folder) return;
	const folderUri = folder.uri.toString();
	if (clients.has(folderUri)) return;

	const newClient = await restartServer();
	if (newClient) clients.set(folderUri, newClient);
}

async function restartAllServers() {
	if (!vscode.workspace.workspaceFolders) return;

	const promises = vscode.workspace.workspaceFolders.map((folder) => {
		return (async () => {
			const folderUri = folder.uri.toString();
			const client = clients.get(folderUri);
			if (!client) return;

			const newClient = await restartServer(client);
			if (newClient) {
				clients.set(folderUri, newClient);
			} else {
				clients.delete(folderUri);
			}
		})();
	});
	await Promise.all(promises);
}

// On start create LSs for all open text documents
// On new open text document, create LS for its workspace
// On restart command, restart all LSs

export async function activate(context: vscode.ExtensionContext) {
	outputChannel = vscode.window.createOutputChannel(NAME, { log: true });

	const pythonExtension = getPythonExtension();
	if (!pythonExtension?.isActive) await pythonExtension?.activate();

	context.subscriptions.push(
		outputChannel,
		// pythonExtension?.exports.environments.onDidChangeActiveEnvironmentPath(
		// 	// TODO: All environments?
		// 	async () => {
		// 		outputChannel?.info("restarting on python environment changed");
		// 		await restartAllServers();
		// 	},
		// ),
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
						outputChannel?.info(`stopping server in folder ${folder.uri}`);
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
