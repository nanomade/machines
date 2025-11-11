import time

# from daqhats import mcc134, HatIDs, HatError, TcTypes, hat_list
from daqhats import mcc134, TcTypes, hat_list


# 0: Hanging in air
# 1: He-return line
# 2: Sample space
# 3: Magnet contact

tc_type = TcTypes.TYPE_K   # change this to the desired thermocouple type
channels = (0, 1, 2, 3)

# Only a single unit is mounted - really the address is just always zero...
address = hat_list()[0].address
hat = mcc134(address)

for channel in channels:
    hat.tc_type_write(channel, tc_type)

while True:
    time.sleep(1)
    values = [0] * 4
    for channel in channels:
        value = hat.t_in_read(channel)
        values[channel] = value
    msg = 'Temperatures. 0: {:.2f}C. 1: {:.2f}C. 2: {:.2f}C. 3: {:3.f}C'
    print(values)
    # print(msg.format(values))
