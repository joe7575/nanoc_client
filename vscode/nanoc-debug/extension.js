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
    const editor = vscode.window.activeTextEditor;
    const env = Object.assign({}, process.env);
    if (session.workspaceFolder) {
      env.NANOC_WORKSPACE = session.workspaceFolder.uri.fsPath;
    }
    if (editor && editor.document.fileName && fs.existsSync(editor.document.fileName)) {
      env.NANOC_ACTIVE = editor.document.fileName;
    }
    return new vscode.DebugAdapterExecutable(command, [], { env });
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
    // Resolve ${file} / ${workspaceFolder} ourselves (attach configs do not
    // always get these substituted by VS Code).
    const editor = vscode.window.activeTextEditor;
    let active = editor ? editor.document.fileName : '';
    if (active && !fs.existsSync(active)) active = '';   // stale/missing tab
    const root = folder ? folder.uri.fsPath : '';
    const expand = (v) => (v || '')
      .replace(/\$\{file\}/g, active)
      .replace(/\$\{workspaceFolder\}/g, root);
    if (config.program) config.program = expand(config.program);
    if (config.source) config.source = expand(config.source);

    if (!config.upload || (config.program && fs.existsSync(config.program))) {
      return config;
    }
    // Active file missing/unknown: fall back to the single .nanoc/.nc file.
    return vscode.workspace.findFiles('**/*.{nanoc,nc}', '**/{.git,node_modules}/**')
      .then((list) => {
        if (list.length === 1) {
          config.program = list[0].fsPath;
          config.source = list[0].fsPath;
          return config;
        }
        vscode.window.showErrorMessage(list.length === 0
          ? 'NanoC: no .nanoc file found in the workspace.'
          : 'NanoC: several .nanoc files — open the one to run, or set "program".');
        return undefined;
      });
  }

  // Called by VS Code after it has substituted ${...} variables.
  resolveDebugConfigurationWithSubstitutedVariables(folder, config) {
    return this.resolveDebugConfiguration(folder, config);
  }
}

function activate(context) {
  outputChannel = vscode.window.createOutputChannel('NanoC');
  context.subscriptions.push(outputChannel);
  try {
    const ext = vscode.extensions.getExtension('joe7575.nanoc-debug');
    log('NanoC debug extension ' + (ext && ext.packageJSON.version || '?') + ' started');
  } catch (e) { /* ignore */ }
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
  context.subscriptions.push(
    vscode.commands.registerCommand('nanoc.openTerminal', openTerminal)
  );
  diagnostics = vscode.languages.createDiagnosticCollection('nanoc');
  context.subscriptions.push(diagnostics);
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(runCheck));
  context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(fixLanguage));
  vscode.workspace.textDocuments.forEach(fixLanguage);
}

function fixLanguage(document) {
  if (document && /\.(nanoc|nc)$/i.test(document.fileName) && document.languageId !== 'nanoc') {
    vscode.languages.setTextDocumentLanguage(document, 'nanoc');
  }
}

function resolveChecker() {
  const configured = vscode.workspace.getConfiguration('nanoc').get('checkPath');
  if (configured) return configured;
  const candidate = path.join(os.homedir(), '.local', 'venvs', 'nanoc', 'bin', 'nanoc-check');
  if (fs.existsSync(candidate)) return candidate;
  return 'nanoc-check';
}

function resolveTui() {
  const configured = vscode.workspace.getConfiguration('nanoc').get('tuiPath');
  if (configured) return configured;
  const candidate = path.join(os.homedir(), '.local', 'venvs', 'nanoc', 'bin', 'nanoc-tui');
  if (fs.existsSync(candidate)) return candidate;
  return 'nanoc-tui';
}

// Open the NanoC terminal (nanoc-tui) in an integrated terminal, using the
// connection info of the active debug session. Keeps the Debug Console for
// debugger messages only.
function openTerminal() {
  const session = vscode.debug.activeDebugSession;
  if (!session || session.type !== 'nanoc') {
    vscode.window.showErrorMessage(
      'NanoC: start/attach a debug session first, then open the terminal.');
    return;
  }
  const cfg = session.configuration || {};
  const args = [
    '--host', String(cfg.host || '127.0.0.1'),
    '--port', String(cfg.port || 41100),
    '--token', String(cfg.token || ''),
  ];
  if (cfg.tls) args.push('--tls');
  if (cfg.serverHostname) args.push('--server-hostname', String(cfg.serverHostname));
  const term = vscode.window.createTerminal({
    name: 'NanoC',
    shellPath: resolveTui(),
    shellArgs: args,
  });
  term.show(true);
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
