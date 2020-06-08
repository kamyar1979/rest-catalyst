from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple

from shapely.geometry import Point


class Gender(Enum):
    Male = 'Male'
    Female = 'Female'


class OrderStatus(Enum):
    Init = 'Init'
    Submitted = 'Submitted'
    Canceled = 'Canceled'
    NeedQuote = 'NeedQuote'
    WithQuote = 'WithQuote'
    QuoteAccepted = 'QuoteAccepted'
    Started = 'Started'
    WithInvoice = 'WithInvoice'
    Finished = 'Finished'
    Done = 'Done'
    WithFeedback = 'WithFeedback'

    def __str__(self):
        return self.value


class OrderTransitionTrigger:
    Submit = 'submit'
    Broadcast = 'broadcast'
    Quote = 'quote'
    Accept = 'accept'
    Deal = 'deal'
    Perform = 'perform'
    Settle = 'settle'
    Cancel = 'cancel'
    Unquote = 'unquote'
    Review = 'review'


@dataclass
class AnswerDetailDTO:
    question_title: Optional[str] = None
    level: Optional[int] = None
    values: Optional[Tuple[str, ...]] = None


class OrderPaymentStatus(Enum):
    Pending = 'Pending'
    Credit = 'Credit'
    Cash = 'Cash'
    PaidByCash = 'PaidByCash'
    PaidByCredit = 'PaidByCredit'


@dataclass
class OrderDTO:
    number: Optional[str] = None
    service_slug: Optional[str] = None
    answers: Optional[Tuple[AnswerDetailDTO, ...]] = None
    customer_mobile: Optional[str] = None
    customer_user_name: Optional[str] = None
    customer_name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    priced_at: Optional[datetime] = None
    delivery_at: Optional[datetime] = None
    delivery_address: Optional[str] = None
    delivery_title: Optional[str] = None
    delivery_location: Optional[Point] = None
    delivery_city_slug: Optional[str] = None
    status: Optional[OrderStatus] = OrderStatus.Init
    total_cost: Optional[Decimal] = None
    voucher_discount: Optional[Decimal] = None
    payable: Optional[Decimal] = None
    provider_user_name: Optional[str] = None
    quotes_count: Optional[int] = 0
    payment_status: Optional[OrderPaymentStatus] = None




