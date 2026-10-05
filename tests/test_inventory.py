import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inventory import parse_bytecode, request_sites

class InventoryTests(unittest.TestCase):
    def test_interface_concrete_constructor_and_sink_calls(self):
        fixture = '''public abstract class com.apple.xsr.net.AbstractRequestMessage implements com.apple.xsr.net.RequestMessage {
}
public class com.apple.xsr.net.UpdateFirmwareRequest extends com.apple.xsr.net.AbstractRequestMessage {
}
public class com.apple.xsr.ManagementController {
  public void handleSystemSetup();
    Code:
       0: invokeinterface #1, 1 // InterfaceMethod com/apple/xsr/net/MessageFactory.newSetTimeRequest:()V
       5: invokevirtual #2 // Method com/apple/xsr/net/AcpxMessageFactory.newGetStatusRequest:()V
      10: invokespecial #3 // Method com/apple/xsr/net/UpdateFirmwareRequest."<init>":()V
      15: invokevirtual #4 // Method com/apple/xsr/net/AcpxConnection.send:()V
}
'''
        methods, types = parse_bytecode(fixture)
        rows = request_sites(methods, types)
        self.assertEqual([r['kind'] for r in rows], ['factory', 'factory', 'request-constructor', 'transport-sink'])
        self.assertTrue(any('newSetTimeRequest' in r['call'] for r in rows))

    def test_empty_mapping_fails(self):
        with self.assertRaisesRegex(ValueError, 'Empty'):
            request_sites([], set())

if __name__ == '__main__': unittest.main()
