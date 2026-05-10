from pycamofox.daemon.models import ExecuteRequest, SessionInfo, CommandResult

def test_execute_request_valid():
    req = ExecuteRequest(command="navigate", args={"url": "https://github.com"})
    assert req.command == "navigate"
    assert req.args["url"] == "https://github.com"

def test_execute_request_defaults():
    req = ExecuteRequest(command="click")
    assert req.args == {}

def test_session_info():
    info = SessionInfo(session_id="abc", tab_id="tab-1", url="")
    assert info.session_id == "abc"
    assert info.tab_id == "tab-1"

def test_command_result_success():
    result = CommandResult(status="ok", result={"url": "https://github.com"})
    assert result.status == "ok"
    assert result.result["url"] == "https://github.com"

def test_command_result_error():
    result = CommandResult(status="error", error="Session not found")
    assert result.status == "error"
    assert result.error == "Session not found"