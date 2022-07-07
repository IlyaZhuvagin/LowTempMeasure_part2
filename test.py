import pyvisa as pv
import pyvisa.constants
import time

rm = pv.ResourceManager()
print(rm.list_resources())


def now():
    return (time.asctime(time.gmtime(time.time())))


class LakeShore():
    def __init__(self, address: str):
        self.address: str = address
        try:
            if "GPIB" in address or "gpib" in address:
                self.inst = rm.open_resource(address, )
            else:
                self.inst = rm.open_resource(
                    address,
                    baud_rate=19200,
                    # parity=pv.constants.Parity.odd,
                    data_bits=8,
                    read_termination="\r"
                )
        except Exception as e:
            print(e)

    def read(self):
        while True:
            try:
                # print(self.inst.query(":DATA?"))
                return self.inst.query_ascii_values('SNAP? 1,2,3,4')
            except Exception as e:
                print(self.address, f": FAIL to read ({e})")
                return None


if __name__ == "__main__":
    R1 = LakeShore("GPIB0::8::INSTR")
    print(R1.read())
