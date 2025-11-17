from tg_logger import logger
import datetime as dt
import time
import functions as f




def gpt_support(smartview: str, timesleep_minutes: int = 5, skip_weekends=True, skip_off_hours=True):
    """
    Определяет характер входящих в заданном смарте, уведомляет в TG об Intersted и кол-ве входящих в смарте
    Планируется: присвоение престатусов лидам, предложение вариантов для ответа
    """
    last_notification_time = dt.datetime.now()
    with open('prompt_for_status.txt', 'r', encoding='utf-8') as file:
        prefix_prompt_for_status = file.read()

    while True:
        report = []
        leads = f.get_leads_from_smartview(smartview)

        # уведомление о количестве входящих в смарте
        if len(leads) > 10 and f.should_send_notification(last_notification_time, skip_weekends, skip_off_hours):
            logger.info(f'\n\nВходящих лидов: {len(leads)}')
            last_notification_time = dt.datetime.now()

        spread = 'auto_support'
        sheet = 'GPT_reply_statuses'
        history = f.get_sheet_range(spread, incom_sheet=sheet, incom_range='A:G')  # загружаем историю проверок писем
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

        for lead in leads:
            print(f"\n{lead['html_url']}")
            email = f.get_last_incoming_email(lead)
            if not email:
                print('Проверка лида отменена, последнее входящее является авто отбивкой')
                continue

            email_id = email.get('id')
            email_at = f.plus_3_hours(email['date_updated'])[:16].replace('T', ' ')

            # пропускаем лид, если входящее письмо уже проверялось
            skip_lead = False
            for row in history[1:]:
                if email_id == row[3] and '##' not in row[6]:
                    skip_lead = True
                    break

            if skip_lead:
                print('GPT анализ письма отменен, письмо уже проверялось')
                continue

            # определяем характер (статус) ответа
            email_context = f.get_context(email, lenght=500)
            email_context = f.hide_numbers(email_context)
            email_context = f.hide_emails(email_context)
            email_context = f.hide_urls(email_context)
            prompt_for_status = prefix_prompt_for_status + email_context

            try:
                gpt_answ = f.ask_gpt(prompt_for_status)
                print(gpt_answ)
            except Exception as e:
                print("Лид будет пропущен, ошибка при обращении к GPT:", e)
                continue

            # переводим Interested письмо и уведомляем в TG
            if 'interested' in gpt_answ:
                prefix_prompt_for_translate = (
                    "Переведи на русский язык письмо, которое я тебе отправляю. "
                    "Дай свой ответ в json форме: {'source_lang': 'тут укажи исходный язык отправленного для перевода "
                    "письма'. Если исходное письмо для перевода было на английском языке, укажи в 'source_lang': "
                    "'Английский',  если письмо было на другом языке, укажи - на каком, например Французский, Немецкий."
                    "translated_text: 'тут вставь текст письма в русском переводе'}. \n"
                    "Если письмо, которое я тебе отправляю, итак на русском языке, "
                    "то translated_text оставь пустой строкой. \n"
                    "Итак вот текст письма для перевода:\n"
                )

                prompt_for_translate = prefix_prompt_for_translate + email_context
                translated_answ = f.ask_gpt(prompt_for_translate)

                # формируем сообщение для уведомления
                try:
                    answ_dict = f.parse_api_response(translated_answ)
                    if answ_dict['source_lang'].capitalize() == 'Русский':
                        text = email_context
                    else:
                        text = answ_dict['translated_text']
                    message = (
                        f"\n\nПохоже {gpt_answ}\n\n"

                        f"Получено: {email_at}\n"
                        f"Исходный язык: {answ_dict['source_lang']}\n\n"
                        f"Тема: {text}\n\n"

                        f"{lead['html_url']}"
                    )
                except Exception as e:
                    print(f'Ошибка при попыпытке распарсинга GPT-ответа с переводом письма: {e}')
                    message = (
                        f"\n\nПохоже {gpt_answ}\n\n"

                        f"Получено: {email_at}\n"
                        f"Тема: {email_context}\n\n"
                        f"{lead['html_url']}"
                    )

                logger.success(message)

            # формируем строку для отчета
            report_row = [
                now,
                lead['id'],
                lead['html_url'],
                email_id,
                email_at,
                email_context,
                gpt_answ,
            ]
            report.append(report_row)

        # добавляем отчет в таблицу истории проеверок
        if report:
            f.add_report_to_sheet(spread, sheet, report)

        print(now)
        time.sleep(timesleep_minutes * 60)


if __name__ == "__main__":
    smart = "776 Incoming"
    logger.info("Скрипт GPT Support запущен")
    while True:
        try:
            gpt_support(smartview=smart, timesleep_minutes=5, skip_weekends=True, skip_off_hours=True)
        except Exception as e:
            logger.info(f'❌ Остановка скрипта GPT Support, ошибка:\n\n{e}')
            time.sleep(60 * 5)
            logger.info(f'✅ Перезапуск скрипта GPT Support...')
