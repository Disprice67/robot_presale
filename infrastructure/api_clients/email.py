from exchangelib import DELEGATE, Account, Credentials, FileAttachment, Mailbox, Message
import os
from typing import Optional
from core import IEmail
from pathlib import Path
from settings.config import Outlook
from core import IRobotLogger


class Email(IEmail):
    def __init__(self, settings_outlook: Outlook, buffer_in: Path, robot_logger: IRobotLogger):
        self.recipients = settings_outlook.recipients.split(', ')
        self.buffer_in = buffer_in
        self.file_list: list[Path] = []
        self.subject: Optional[str] = None
        self.sender: Optional[str] = None
        self.body: Optional[str] = None
        self.robot_logger = robot_logger

        self.credentials = Credentials(
            settings_outlook.username_outlook,
            settings_outlook.password_outlook
        )
        self.account = Account(
            primary_smtp_address=settings_outlook.username_outlook,
            credentials=self.credentials,
            autodiscover=True,
            access_type=DELEGATE
        )

    def get_file_list(self) -> list[Path]:
        return self.file_list

    def clear_file_list(self) -> None:
        self.file_list.clear()

    def remove_sender_email(self) -> None:
        self.recipients.remove(self.sender)

    def download_attachments(self,) -> bool:
        """Сохраняет вложения из входящих писем в указанный каталог."""
        try:
            for item in self.account.inbox.all():
                self.sender = item.sender.email_address
                if self.sender not in self.recipients:
                    self.recipients.append(self.sender)
                self.subject = item.subject

                for attachment in item.attachments:
                    if attachment.name[attachment.name.rfind('.') - 1] in ('D', 'Y'):
                        item.delete()
                        return False
                    if isinstance(attachment, FileAttachment) and attachment.name.endswith('.xlsx'):
                        self.robot_logger.info(f'Найден excel в письме {attachment.name}.')
                        path = self.buffer_in / attachment.name
                        with open(path, 'wb') as f:
                            f.write(attachment.content)
                        self.file_list.append(path)

                if self.file_list:
                    item.delete()
                    return True
                item.delete()
        except Exception as e:
            self.robot_logger.error(f"Ошибка при обработке писем: {e}")
        return False

    def send_email(self, attachments: Path, sheet_name: str):
        """
        Send an email.
        Parameters
        ----------
        account : Account object
        subject : str
        body : str
        recipients : list of str
            Each str is and email adress
        attachments : list of tuples or None
            (filename, binary contents)
        Examples
        --------
        >>> send_email(account, 'Subject line', 'Hello!', ['info@example.com'])
        """
        try:
            to_recipients = [Mailbox(email_address=recipient) for recipient in self.recipients]
            # Create message
            m = Message(account=self.account,
                        folder=self.account.sent,
                        subject=self.subject,
                        body=f'Обработана страница << {sheet_name} >>.',
                        to_recipients=to_recipients)
            # attach files
            if attachments:
                with open(attachments, 'rb') as f:
                    attachment_content = f.read()
                file = FileAttachment(name=attachments.name , content=attachment_content)
                m.attach(file)
            m.send_and_save()
            attachments.unlink()
        except Exception as e:
            self.robot_logger.error(f'Ошибка при отправке письма {e}')
