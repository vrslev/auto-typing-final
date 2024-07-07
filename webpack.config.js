// @ts-check
/** @type import('webpack').Configuration */
const extensionConfig = {
	target: "node",
	entry: "./extension.ts",
	mode: "none",

	output: {
		path: require("path").resolve(__dirname, "dist"),
		filename: "extension.js",
		libraryTarget: "commonjs2",
		devtoolModuleFilenameTemplate: "../[resource-path]",
	},
	devtool: "source-map",
	externals: {
		vscode: "commonjs vscode",
	},
	resolve: {
		extensions: [".js"],
	},
	module: {
		rules: [
			{
				test: /\.ts$/,
				exclude: /node_modules/,
				use: [
					{
						loader: "ts-loader",
					},
				],
			},
		],
	},
};

module.exports = [extensionConfig];
