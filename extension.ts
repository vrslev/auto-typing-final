import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import * as vscodeLanguageClient from "vscode-languageclient/node";

let languageClient: vscodeLanguageClient.LanguageClient | undefined;
let outputChannel: vscode.LogOutputChannel | undefined;

const serverId = "auto-typing-final";
const serverName = serverId;

function getPythonExtension():
	| vscode.Extension<{
			environments: {
				onDidChangeActiveEnvironmentPath: (event: any) => any;
				getActiveEnvironmentPath: () => { path: string };
				resolveEnvironment: (environment: { path: string }) => Promise<
					{ executable: { uri?: { fsPath: string } } } | undefined
				>;
			};
	  }>
	| undefined {
	return vscode.extensions.getExtension("ms-python.python");
}

async function findExecutable() {
	const extension = getPythonExtension();
	if (!extension) return;
	const environmentPath =
		extension.exports.environments.getActiveEnvironmentPath();
	if (!environmentPath) return;
	const environment =
		await extension.exports.environments.resolveEnvironment(environmentPath);
	if (!environment) return;
	const fsPath = environment.executable.uri?.fsPath;
	if (!fsPath) return;
	const parsedPath = path.parse(fsPath);
	const lspServerPath = path.format({
		base: "auto-typing-final-lsp-server",
		dir: parsedPath.dir,
		root: parsedPath.root,
	});
	if (!fs.existsSync(lspServerPath)) return;
	return lspServerPath;
}

async function restartServer() {
	await languageClient?.stop();

	const executable = await findExecutable();
	if (!executable) return;

	const serverOptions = {
		command: executable,
		args: [],
		options: { env: process.env },
	};
	const clientOptions = {
		documentSelector: [
			{ scheme: "file", language: "python" },
			{ scheme: "untitled", language: "python" },
		],
		outputChannel: outputChannel,
		traceOutputChannel: outputChannel,
		revealOutputChannelOn: vscodeLanguageClient.RevealOutputChannelOn.Never,
	};

	languageClient = new vscodeLanguageClient.LanguageClient(
		serverId,
		serverName,
		serverOptions,
		clientOptions,
	);
	await languageClient.start();
}

export async function activate(context: vscode.ExtensionContext) {
	const pythonExtension = getPythonExtension();
	if (!pythonExtension?.isActive) await pythonExtension?.activate();

	outputChannel = vscode.window.createOutputChannel(serverName, { log: true });

	context.subscriptions.push(
		outputChannel,
		pythonExtension?.exports.environments.onDidChangeActiveEnvironmentPath(
			async () => {
				await restartServer();
			},
		),
		vscode.commands.registerCommand(`${serverName}.restart`, async () => {
			await restartServer();
		}),
	);

	await restartServer();
}

export async function deactivate() {
	await languageClient?.stop();
}
