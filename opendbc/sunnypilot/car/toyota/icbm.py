"""Toyota TSS3 Intelligent Cruise Button Management."""

from opendbc.car import DT_CTRL, structs
from opendbc.car.can_definitions import CanData
from opendbc.car.toyota.tss3 import TSS3_SOURCE_BUS
from opendbc.sunnypilot.car.intelligent_cruise_button_management_interface_base import IntelligentCruiseButtonManagementInterfaceBase

SendButtonState = structs.IntelligentCruiseButtonManagement.SendButtonState

CRUISE_BUTTONS_ADDRESS = 0x0FE
BUTTON_SEND_INTERVAL = 0.05


def create_tss3_cruise_button_command(stock: bytes, send_button: SendButtonState) -> CanData | None:
  """Clone the OEM 0x0FE and change only a RES or SET button/inverse pair."""
  if len(stock) != 32 or send_button not in (SendButtonState.increase, SendButtonState.decrease):
    return None

  # Never override a physical button press or an invalid complementary pair.
  neutral = (not stock[3] & 0x80 and stock[6] & 0x80 and
             not stock[4] & 0x80 and stock[7] & 0x40 and
             not stock[4] & 0x40 and stock[7] & 0x20 and
             not stock[7] & 0x04)
  if not neutral:
    return None

  dat = bytearray(stock)
  if send_button == SendButtonState.increase:
    dat[3] |= 0x80   # RES_BUTTON
    dat[6] &= 0x7F  # RES_BUTTON_MIRROR_N
  else:
    dat[4] |= 0x80   # SET_BUTTON
    dat[7] &= 0xBF  # SET_BUTTON_MIRROR_N
  return CanData(CRUISE_BUTTONS_ADDRESS, bytes(dat), TSS3_SOURCE_BUS)


class IntelligentCruiseButtonManagementInterface(IntelligentCruiseButtonManagementInterfaceBase):
  def update(self, CS, CC_SP, frame: int) -> list[CanData]:
    self.CC_SP = CC_SP
    self.ICBM = CC_SP.intelligentCruiseButtonManagement
    self.frame = frame

    if self.ICBM.sendButton == SendButtonState.none:
      return []
    if (self.frame - self.last_button_frame) * DT_CTRL < BUTTON_SEND_INTERVAL:
      return []

    msg = create_tss3_cruise_button_command(CS.tss3_cruise_buttons, self.ICBM.sendButton)
    if msg is None:
      return []

    self.last_button_frame = self.frame
    return [msg]
