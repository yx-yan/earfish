// Runs earfish inside this binary. macOS grants Microphone access to the
// binary that makes the call, so a script that starts Python would ask as Python.

#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#ifndef MODULE
#define MODULE L"earfish.app"
#endif

static void log_to_file(void) {
    char path[1024];
    snprintf(path, sizeof path, "%s/Library/Logs/Earfish.log", getenv("HOME"));
    freopen(path, "a", stdout);
    freopen(path, "a", stderr);
}

int main(int argc, char **argv) {
    if (!isatty(STDERR_FILENO)) {
        log_to_file();
    }
    setenv("PYTHONUTF8", "1", 1);  // Apps opened from Finder have no locale.
    setenv("PYTHONUNBUFFERED", "1", 1);

    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.safe_path = 1;
    PyStatus status = PyConfig_SetBytesString(&config, &config.executable, VENV_PYTHON);
    if (!PyStatus_Exception(status)) {
        status = PyConfig_SetString(&config, &config.run_module, MODULE);
    }
    if (!PyStatus_Exception(status)) {
        status = PyConfig_SetBytesArgv(&config, argc, argv);
    }
    if (!PyStatus_Exception(status)) {
        status = Py_InitializeFromConfig(&config);
    }
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }
    return Py_RunMain();
}
