"""身份证号校验"""
import re


def validate_id_card(number: str) -> str:
    """校验18位身份证号，返回清洗后的号码。失败则抛出 ValueError。"""
    number = str(number).strip().upper()
    if not re.match(r'^\d{17}[\dX]$', number):
        raise ValueError("身份证号格式不正确，应为18位数字（末位可为X）")
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_chars = "10X98765432"
    total = sum(int(number[i]) * weights[i] for i in range(17))
    if check_chars[total % 11] != number[17]:
        raise ValueError("身份证号校验码不正确")
    return number


def mask_id_card(number: str) -> str:
    """脱敏身份证号：前3后4，中间用 * 替换"""
    if not number or len(number) < 8:
        return number or ""
    return number[:3] + "*" * (len(number) - 7) + number[-4:]


def mask_phone(phone: str | None) -> str:
    """脱敏手机号：前3后4，中间用 **** 替换"""
    if not phone or len(phone) < 7:
        return phone or ""
    return phone[:3] + "****" + phone[-4:]
