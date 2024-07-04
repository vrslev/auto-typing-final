// @ts-check

/** @type import('webpack').Configuration */
const extensionConfig = {
  target: "node",
  mode: "none",

  entry: "./extension.js",
  output: {
    path: require("path").resolve(__dirname, "dist"),
    filename: "extension.js",
    libraryTarget: "commonjs2",
  },
  externals: {
    vscode: "commonjs vscode",
  },
  resolve: {
    extensions: [".js"],
  },
  devtool: "nosources-source-map",
};

module.exports = [extensionConfig];
