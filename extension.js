// @ts-check
const vscode = require("vscode");
const vscodeLanguageClient = require("vscode-languageclient/node");

async function getPythonExtension() {
  /** @type {vscode.Extension<{environments: {onDidChangeActiveEnvironmentPath: ((event) => any)}}> | undefined} */
  const pythonExtension = vscode.extensions.getExtension("ms-python.python");
  if (!pythonExtension) return;
  if (!pythonExtension.isActive) await pythonExtension.activate();
  return pythonExtension;
}

/** @type {vscodeLanguageClient.LanguageClient | undefined} */
let lsClient;
let restartInProgress = false;
let restartQueued = false;
let outputChannel = undefined;
// let disposables = [];

async function restartServer() {
  if (restartInProgress) {
    if (!restartQueued) restartQueued = true;
    return;
  }
  if (lsClient) {
    await lsClient.stop()
    // disposables.forEach((d) => d.dispose());
    // disposables = [];
  }
  let serverOptions = {
    command: "/Users/lev/code/auto-typing-final/.venv/bin/python",
    args: ["/Users/lev/code/auto-typing-final/auto_typing_final/lsp.py"],
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

  lsClient = new vscodeLanguageClient.LanguageClient("auto-typing-final", "auto-typing-final", serverOptions, clientOptions);
  await lsClient.start()
}

module.exports = {
  /**
   * @param context {vscode.ExtensionContext}
   **/
  activate: async (context) => {
    outputChannel = vscode.window.createOutputChannel("auto-typing.final", { log: true });

    context.subscriptions.push(
      outputChannel,
      (await getPythonExtension())?.exports.environments.onDidChangeActiveEnvironmentPath(async (event) => {
        await restartServer();
      }),
      // vscode.workspace.onDidChangeConfiguration(async (event) => {
      //   if (["auto-typing-final.path"].some((s) => event.affectsConfiguration(s))) await restartServer();
      // }),
      vscode.commands.registerCommand(`auto-typing-final.restart`, async () => {
        await restartServer();
      }),
    );

    await restartServer();
  },
  deactivate: async () => {
    await lsClient?.stop()
  }
};
