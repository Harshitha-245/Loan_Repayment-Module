from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

class LoanCalculator:

    GST_RATE = Decimal("0.18")

    @staticmethod
    def calculate_emi(principal: Decimal, annual_rate: Decimal, tenure: int):

        monthly_rate = annual_rate / Decimal("100") / Decimal("12")

        if monthly_rate <= 0:
            raise ValueError("Interest rate must be greater than 0")

        r = monthly_rate
        n = tenure
        P = principal

        emi = (P * r * (1 + r) ** n) / ((1 + r) ** n - 1)

        return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def generate_schedule(
        principal: Decimal,
        annual_rate: Decimal,
        tenure: int,
        first_emi_date
    ):

        emi_amount = LoanCalculator.calculate_emi(
            principal, annual_rate, tenure
        )

        monthly_rate = annual_rate / Decimal("100") / Decimal("12")

        remaining = principal
        schedule = []

        for emi_number in range(1, tenure + 1):

            opening = remaining

            interest = (opening * monthly_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            principal_component = (emi_amount - interest).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if emi_number == tenure:
                principal_component = opening
                interest = (emi_amount - principal_component).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            closing = (opening - principal_component).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            gst = (interest * LoanCalculator.GST_RATE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            schedule.append({
                "emi_number": emi_number,
                "due_date": first_emi_date + relativedelta(months=emi_number - 1),
                "opening_principal": opening,
                "principal_component": principal_component,
                "interest_component": interest,
                "gst_amount": gst,
                "emi_amount": emi_amount,
                "closing_principal": closing
            })

            remaining = closing

        return schedule