import pytest
import structlog
import json
from io import StringIO

def test_structured_logging_format():
    # Capture output in memory
    stream = StringIO()
    
    # Configure a temporary strict JSON logger for the test
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(file=stream),
    )
    
    logger = structlog.get_logger()
    
    # Simulate a security event
    logger.warning("security_event", ip="192.168.1.1", action="auto_banned")
    
    log_output = stream.getvalue()
    
    # Mathematically prove the output is valid JSON and contains our keys
    try:
        parsed_log = json.loads(log_output)
    except json.JSONDecodeError:
        pytest.fail("Logger did not output valid JSON")
        
    assert parsed_log["event"] == "security_event"
    assert parsed_log["ip"] == "192.168.1.1"
    assert parsed_log["action"] == "auto_banned"