// @ts-check
const { exists, stat, existsSync } = require("fs");
const path = require("path");
const fs = require("fs");
const vscode = require("vscode");
const vscodeLanguageClient = require("vscode-languageclient/node");

/** @type {vscodeLanguageClient.LanguageClient | undefined} */
let languageClient;
let outputChannel;

const serverId = "auto-typing-final";
const serverName = serverId;

/**
 * @returns {vscode.Extension<{
 *   environments: {
 *     onDidChangeActiveEnvironmentPath: ((event) => any),
 *     getActiveEnvironmentPath: () => { path: string },
 *     resolveEnvironment: (environment: { path: string }) => Promise<{ executable: { uri?: { fsPath: string } } } | undefined>,
 *   }
 * }> | undefined}
 **/
function getPythonExtension() {
  return vscode.extensions.getExtension("ms-python.python");
}

async function findExecutable() {
  const extension = getPythonExtension();
  if (!extension) return;
  const environmentPath = extension.exports.environments.getActiveEnvironmentPath();
  if (!environmentPath) return;
  const environment = await extension.exports.environments.resolveEnvironment(environmentPath);
  if (!environment) return;
  const fsPath = environment.executable.uri?.fsPath;
  if (!fsPath) return;
  const parsedPath = path.parse(fsPath);
  const lspServerPath = path.format({ base: "auto-typing-final-lsp-server", dir: parsedPath.dir, root: parsedPath.root })
  if (!fs.existsSync(lspServerPath)) return;
  return lspServerPath
}

async function restartServer() {
  await languageClient?.stop()

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

  languageClient = new vscodeLanguageClient.LanguageClient(serverId, serverName, serverOptions, clientOptions);
  await languageClient.start()
}

module.exports = {
  /**
   * @param context {vscode.ExtensionContext}
   **/
  async activate(context) {
    /** @type {vscode.Extension<{environments: {onDidChangeActiveEnvironmentPath: ((event) => any)}}> | undefined} */
    const pythonExtension = vscode.extensions.getExtension("ms-python.python");
    if (!pythonExtension?.isActive) await pythonExtension?.activate();

    outputChannel = vscode.window.createOutputChannel(serverName, { log: true });

    context.subscriptions.push(
      outputChannel,
      pythonExtension?.exports.environments.onDidChangeActiveEnvironmentPath(async (event) => {
        await restartServer();
      }),
      // vscode.workspace.onDidChangeConfiguration(async (event) => {
      //   if (["auto-typing-final.path"].some((s) => event.affectsConfiguration(s))) await restartServer();
      // }),
      vscode.commands.registerCommand(`${serverName}.restart`, async () => {
        await restartServer();
      }),
    );

    await restartServer();
  },
  async deactivate() {
    await languageClient?.stop()
  }
};
