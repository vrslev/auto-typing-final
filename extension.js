// @ts-check
const vscode = require("vscode");
const vscodeLanguageClient = require("vscode-languageclient/node");

/** @type {vscodeLanguageClient.LanguageClient | undefined} */
let languageClient;
let outputChannel = undefined;

async function restartServer() {
  const serverOptions = {
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

  await languageClient?.stop()
  languageClient = new vscodeLanguageClient.LanguageClient("auto-typing-final", "auto-typing-final", serverOptions, clientOptions);
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

    outputChannel = vscode.window.createOutputChannel("auto-typing.final", { log: true });

    context.subscriptions.push(
      outputChannel,
      pythonExtension?.exports.environments.onDidChangeActiveEnvironmentPath(async (event) => {
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
  async deactivate() {
    await languageClient?.stop()
  }
};
