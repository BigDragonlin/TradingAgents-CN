import os
from app_email.receice_email.receiver import (
    receive_emails,
    EmailReceiveError,
    mark_email_as_seen,
)
from tradingagents.utils.logging_manager import get_logger
from app_email.scheduler_service import process_email_job

logger = get_logger("email_receive_service")


class EmailReceiveService:
    def __init__(self):
        # 从环境变量获取配置
        self.imap_host = os.getenv("IMAP_HOST", "imap.qq.com")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        self.username = os.getenv("IMAP_USER") or os.getenv("EMAIL_USER")
        self.password = os.getenv("IMAP_PASS") or os.getenv("EMAIL_PASSWORD")
        self.mailbox = os.getenv("IMAP_MAILBOX", "INBOX")
        self.criteria = os.getenv("IMAP_CRITERIA", "UNSEEN")

        # 轮询间隔（秒）
        self.poll_interval = int(os.getenv("EMAIL_POLL_INTERVAL_SECONDS", "30"))

        # 预览长度
        self.preview_len = int(os.getenv("EMAIL_PREVIEW_LEN", "500"))

        # 要打印的字段
        self.print_fields = {
            f.strip().lower()
            for f in os.getenv("EMAIL_PRINT_FIELDS", "from,subject,body").split(",")
            if f.strip()
        }

        # 已处理的邮件去重
        self.seen_keys = set()

    def validate_config(self):
        """验证配置是否完整"""
        if not self.username or not self.password:
            logger.error(
                "邮箱用户名或密码未配置，请设置 IMAP_USER 和 IMAP_PASS 环境变量"
            )
            return False
        return True

    def process_email(self, email_data):
        """处理接收到的邮件"""
        # 这里可以添加邮件处理逻辑，比如：
        # - 解析邮件内容
        # - 触发相应的分析任务
        # - 发送通知等

        logger.info(
            f"新邮件: {email_data.get('subject')} from {email_data.get('from')}"
        )

        # 打印邮件内容（可选）
        if "from" in self.print_fields:
            print(f"From: {email_data.get('from')}")
        if "subject" in self.print_fields:
            print(f"Subject: {email_data.get('subject')}")
        if "body" in self.print_fields:
            body = email_data.get("body", "")
            process_email_job(body, email_data.get("from"))
        print("-" * 60)

    def poll_emails(self):
        """轮询接收邮件（单次执行）"""
        if not self.validate_config():
            return

        try:
            results = receive_emails(
                imap_host=self.imap_host,
                imap_port=self.imap_port,
                username=self.username,
                password=self.password,
                mailbox=self.mailbox,
                criteria=self.criteria,
                limit=None,
            )

            new_count = 0
            for msg in results:
                # 使用 (发件人, 主题, 内容前100字符) 作为去重键
                key = (
                    msg.get("from"),
                    msg.get("subject"),
                    msg.get("body", "")[:100] if msg.get("body") else "",
                )

                if key in self.seen_keys:
                    continue

                self.seen_keys.add(key)
                new_count += 1

                # 处理后标记为已读（如果当前查询使用 UNSEEN，则避免重复处理）
                msg_id = msg.get("id")
                if msg_id:
                    try:
                        marked = mark_email_as_seen(
                            imap_host=self.imap_host,
                            imap_port=self.imap_port,
                            username=self.username,
                            password=self.password,
                            mailbox=self.mailbox,
                            message_id=str(msg_id),
                        )
                        if marked:
                            # TODO 回执
                            logger.debug(f"邮件已标记为已读: id={msg_id}")
                        else:
                            logger.warning(f"标记已读失败: id={msg_id}")
                    except Exception as e:
                        logger.warning(f"标记已读异常: id={msg_id}, err={e}")
                self.process_email(msg)
            if new_count == 0:
                return
            else:
                logger.info(f"处理了 {new_count} 封新邮件")

        except EmailReceiveError as e:
            logger.error(f"邮件接收错误: {e}")
        except Exception as e:
            logger.exception(f"邮件接收服务异常: {e}")


# 全局服务实例
email_receive_service = EmailReceiveService()


def poll_and_receive_emails():
    """用于调度的邮件接收函数"""
    email_receive_service.poll_emails()
