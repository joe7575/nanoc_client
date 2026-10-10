// NanoC debugger extension: spawns the nanoc-dap adapter.
// The DAP `attach`/`launch` arguments (host, port, token, source) are sent by
// VS Code to the adapter, so this extension only has to locate and start it.
const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
const path = require('path');

function resolveCommand(configuration) {
  if (configuration && configuration.dapPath) {
    return configuration.dapPath;
  }
  const configured = vscode.workspace.getConfiguration('nanoc').get('dapPath');
  if (configured) {
    return configured;
  }
  // Default install location used by the setup instructions.
  const candidate = path.join(os.homedir(), '.local', 'venvs', 'nanoc', 'bin', 'nanoc-dap');
  if (fs.existsSync(candidate)) {
    return candidate;
  }
  // Fall back to PATH.
  return 'nanoc-dap';
}

class NanocAdapterFactory {
  createDebugAdapterDescriptor(session) {
    const command = resolveCommand(session.configuration);
    return new vscode.DebugAdapterExecutable(command, []);
  }
}

class NanocConfigProvider {
  provideDebugConfigurations() {
    return [
      {
        type: 'nanoc',
        request: 'attach',
        name: 'NanoC: attach',
        host: '127.0.0.1',
        port: 41100,
        token: '',
      },
    ];
  }

  resolveDebugConfiguration(folder, config) {
    if (!config.type && !config.request && !config.name) {
      config.type = 'nanoc';
      config.request = 'attach';
      config.name = 'NanoC: attach';
      config.host = '127.0.0.1';
      config.port = 41100;
      config.token = '';
    }
    return config;
  }
}

function activate(context) {
  context.subscriptions.push(
    vscode.debug.registerDebugAdapterDescriptorFactory('nanoc', new NanocAdapterFactory())
  );
  context.subscriptions.push(
    vscode.debug.registerDebugConfigurationProvider('nanoc', new NanocConfigProvider())
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
