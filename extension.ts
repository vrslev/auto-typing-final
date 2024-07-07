import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import type * as vscodeLanguageClient from "vscode-languageclient/node";
import {
	LanguageClient,
	type LanguageClientOptions,
	RevealOutputChannelOn,
} from "vscode-languageclient/node";

const NAME = "auto-typing-final";
const PYTHON_EXTENSION_ID = "ms-python.python";
const LSP_SERVER_EXECUTABLE_NAME = "auto-typing-final-lsp-server";

let languageClient: vscodeLanguageClient.LanguageClient | undefined;
let outputChannel: vscode.LogOutputChannel | undefined;

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
	return vscode.extensions.getExtension(PYTHON_EXTENSION_ID);
}

async function findExecutable() {
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

	return lspServerPath;
}

async function restartServer() {
	await languageClient?.stop();
	outputChannel?.info("stopped server");

	const executable = await findExecutable();
	outputChannel?.info(`using executable at ${executable}`);
	if (!executable) {
		outputChannel?.info("not found executable");
		return;
	}

	const serverOptions = {
		command: executable,
		args: [],
		options: { env: process.env },
	};
	const clientOptions: LanguageClientOptions = {
		documentSelector: [
			{ scheme: "file", language: "python" },
			{ scheme: "untitled", language: "python" },
		],
		outputChannel: outputChannel,
		traceOutputChannel: outputChannel,
		revealOutputChannelOn: RevealOutputChannelOn.Never,
	};
	languageClient = new LanguageClient(NAME, serverOptions, clientOptions);
	await languageClient.start();
	outputChannel?.info("started server");
}

export async function activate(context: vscode.ExtensionContext) {
	const pythonExtension = getPythonExtension();
	if (!pythonExtension?.isActive) await pythonExtension?.activate();

	outputChannel = vscode.window.createOutputChannel(NAME, { log: true });

	context.subscriptions.push(
		outputChannel,
		pythonExtension?.exports.environments.onDidChangeActiveEnvironmentPath(
			async () => {
				outputChannel?.info("restarting on python environment changed");
				await restartServer();
			},
		),
		vscode.commands.registerCommand(`${NAME}.restart`, async () => {
			outputChannel?.info(`restarting from ${NAME}.restart`);
			await restartServer();
		}),
	);

	await restartServer();
}

export async function deactivate() {
	await languageClient?.stop();
}
