// NanoC debugger extension: spawns the nanoc-dap adapter.
// The DAP `attach`/`launch` arguments (host, port, token, source) are sent by
// VS Code to the adapter, so this extension only has to locate and start it.
const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');

let outputChannel;
let diagnostics;

function log(line) {
  if (outputChannel) outputChannel.appendLine(line);
}

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
  outputChannel = vscode.window.createOutputChannel('NanoC');
  context.subscriptions.push(outputChannel);
  context.subscriptions.push(
    vscode.debug.registerDebugAdapterDescriptorFactory('nanoc', new NanocAdapterFactory())
  );
  context.subscriptions.push(
    vscode.debug.registerDebugConfigurationProvider('nanoc', new NanocConfigProvider())
  );
  context.subscriptions.push(
    vscode.commands.registerCommand('nanoc.upload', uploadProgram)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand('nanoc.download', downloadProgram)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand('nanoc.check', checkProgram)
  );
  diagnostics = vscode.languages.createDiagnosticCollection('nanoc');
  context.subscriptions.push(diagnostics);
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(runCheck));
  vscode.workspace.textDocuments.forEach(runCheck);
}

function resolveChecker() {
  const configured = vscode.workspace.getConfiguration('nanoc').get('checkPath');
  if (configured) return configured;
  const candidate = path.join(os.homedir(), '.local', 'venvs', 'nanoc', 'bin', 'nanoc-check');
  if (fs.existsSync(candidate)) return candidate;
  return 'nanoc-check';
}

function runCheck(document) {
  if (!document || (document.languageId !== 'nanoc' && !/\.(nanoc|nc)$/.test(document.fileName))) {
    return;
  }
  if (document.isUntitled || !document.fileName) return;
  cp.execFile(resolveChecker(), [document.fileName], (err, stdout, stderr) => {
    const out = (stdout || '') + (stderr || '');
    const items = [];
    for (const line of out.split(/\r?\n/)) {
      const m = line.match(/^(.+?):(\d+):\s*error:\s*(.*)$/);
      if (!m) continue;
      const ln = Math.max(0, parseInt(m[2], 10) - 1);
      items.push(new vscode.Diagnostic(
        new vscode.Range(ln, 0, ln, 1000), m[3], vscode.DiagnosticSeverity.Error));
    }
    diagnostics.set(document.uri, items);
  });
}

function checkProgram() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  runCheck(editor.document);
  vscode.window.setStatusBarMessage(
    'NanoC: checked ' + path.basename(editor.document.fileName), 3000);
}

function activeSession() {
  const session = vscode.debug.activeDebugSession;
  if (!session || session.type !== 'nanoc') {
    vscode.window.showErrorMessage('NanoC: no active debug session. Start one (F5) first.');
    return null;
  }
  return session;
}

async function uploadProgram() {
  const session = activeSession();
  if (!session) return;
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage('NanoC: no active editor.');
    return;
  }
  const text = editor.document.getText();
  try {
    const res = await session.customRequest('nanoc/upload', { text });
    log('Uploaded ' + editor.document.fileName);
    if (res && res.message) log(res.message);
    outputChannel.show(true);
    vscode.window.setStatusBarMessage(
      'NanoC: uploaded ' + path.basename(editor.document.fileName), 3000);
  } catch (err) {
    log('Upload failed: ' + err.message);
    outputChannel.show(true);
    vscode.window.showErrorMessage('NanoC upload failed: ' + err.message);
  }
}

async function downloadProgram() {
  const session = activeSession();
  if (!session) return;
  try {
    const res = await session.customRequest('nanoc/download', {});
    log('Downloaded program (' + (res.text || '').length + ' bytes)');
    outputChannel.show(true);
    const doc = await vscode.workspace.openTextDocument({
      language: 'nanoc',
      content: res.text || '',
    });
    await vscode.window.showTextDocument(doc, { preview: false });
  } catch (err) {
    log('Download failed: ' + err.message);
    outputChannel.show(true);
    vscode.window.showErrorMessage('NanoC download failed: ' + err.message);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
