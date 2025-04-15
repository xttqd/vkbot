from vkbottle import Keyboard, KeyboardButtonColor, Text

def get_start_keyboard():
    """
    Создает стартовую клавиатуру с кнопками для начала заполнения формы и просмотра заявок
    """
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Заполнить заявку"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Мои заявки"), color=KeyboardButtonColor.SECONDARY)
    return keyboard

def get_form_keyboard():
    """
    Создает клавиатуру для процесса заполнения формы с кнопкой отмены
    """
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_submit_keyboard():
    """
    Создает клавиатуру для отправки заполненной формы с кнопками отправки и отмены
    """
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Отправить"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_ticket_detail_keyboard(ticket_id: str):
    """
    Создает клавиатуру для просмотра деталей заявки с кнопками возврата и удаления

    Args:
        ticket_id: Идентификатор заявки для передачи в команду удаления
    """
    print(f"Создаем клавиатуру для заявки: {ticket_id}") # Оставляем print пока, позже можно заменить на логгирование
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Мои заявки"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Удалить заявку"), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("Заполнить заявку"), color=KeyboardButtonColor.PRIMARY)
    return keyboard 