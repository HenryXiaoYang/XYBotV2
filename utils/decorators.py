from functools import wraps
from typing import Callable, Union

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()


def schedule(
        trigger: Union[str, CronTrigger, IntervalTrigger],
        **trigger_args
) -> Callable:
    """
    定时任务装饰器
    
    例子:

    - @schedule('interval', seconds=30)
    - @schedule('cron', hour=8, minute=30, second=30)
    - @schedule('date', run_date='2024-01-01 00:00:00')
    """

    def decorator(func: Callable):
        job_id = f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)

        setattr(wrapper, '_is_scheduled', True)
        setattr(wrapper, '_schedule_trigger', trigger)
        setattr(wrapper, '_schedule_args', trigger_args)
        setattr(wrapper, '_job_id', job_id)

        return wrapper

    return decorator


def add_job_safe(scheduler: AsyncIOScheduler, job_id: str, func: Callable, bot,
                 trigger: Union[str, CronTrigger, IntervalTrigger], **trigger_args):
    """添加函数到定时任务中，如果存在则先删除现有的任务"""
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    scheduler.add_job(func, trigger, args=[bot], id=job_id, **trigger_args)


def remove_job_safe(scheduler: AsyncIOScheduler, job_id: str):
    """从定时任务中移除任务"""
    try:
        scheduler.remove_job(job_id)
    except:
        pass


def on_text_message(priority=50):
    """文本消息装饰器"""

    def decorator(func):
        if callable(priority):  # 无参数调用时
            f = priority
            setattr(f, '_event_type', 'text_message')
            setattr(f, '_priority', 50)
            return f
        # 有参数调用时
        setattr(func, '_event_type', 'text_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_image_message(priority=50):
    """图片消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'image_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'image_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_voice_message(priority=50):
    """语音消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'voice_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'voice_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_emoji_message(priority=50):
    """表情消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'emoji_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'emoji_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_file_message(priority=50):
    """文件消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'file_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'file_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_quote_message(priority=50):
    """引用消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'quote_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'quote_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_video_message(priority=50):
    """视频消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'video_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'video_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_pat_message(priority=50):
    """拍一拍消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'pat_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'pat_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_at_message(priority=50):
    """被@消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'at_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'at_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_system_message(priority=50):
    """系统消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'system_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'system_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_revoke_message(priority=50):
    """撤回消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'revoke_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'revoke_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)


def on_other_message(priority=50):
    """其他消息装饰器"""

    def decorator(func):
        if callable(priority):
            f = priority
            setattr(f, '_event_type', 'other_message')
            setattr(f, '_priority', 50)
            return f
        setattr(func, '_event_type', 'other_message')
        setattr(func, '_priority', min(max(priority, 0), 99))
        return func

    return decorator if not callable(priority) else decorator(priority)
