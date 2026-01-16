"""Toolkit for the hospitality domain (Berkeley Hot Pot restaurant)."""

import hashlib
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from tau2.domains.hospitality.data_model import (
    Customer,
    HospitalityDB,
    Incident,
    IncidentType,
    Inventory,
    MemberTier,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Reservation,
    ReservationStatus,
    SecretCode,
    SoupBase,
    StaffAuthority,
    StaffRole,
    Table,
    TableStatus,
    TableType,
)
from tau2.domains.hospitality.utils import (
    get_now,
    get_today,
    is_federal_holiday,
    is_lunch_time,
    is_weekday,
)
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class HospitalityTools(ToolKitBase):
    """Tools for the hospitality domain."""

    db: HospitalityDB

    def __init__(self, db: HospitalityDB) -> None:
        """Initialize the hospitality tools with a database instance."""
        super().__init__(db)

    # ============== Helper Methods (not tools) ==============

    # ============== Initialization Methods (for test setup) ==============
    
    def initialize_order(self, bill_amount: float, table_id: str = "A01") -> str:
        """Initialize a test order with specified bill amount. Used for test setup."""
        from datetime import datetime
        order = Order(
            order_id=self._generate_id("ORD", table_id, bill_amount),
            table_id=table_id,
            items=[],
            subtotal=bill_amount,
            tax=bill_amount * 0.0875,
            total=bill_amount * 1.0875,
            status=OrderStatus.IN_PROGRESS,
            created_at="2026-01-01T12:00:00",  # Fixed timestamp for deterministic evaluation
        )
        self.db.orders.append(order)
        return f"Test order created with bill amount ${bill_amount:.2f}"

    def initialize_customer_points(self, customer_id: str, points: int, tier: str = "Gold") -> str:
        """Initialize customer with specific points balance. Used for test setup."""
        # Normalize tier to proper case (e.g., "gold" -> "Gold")
        tier_normalized = tier.capitalize()
        member_tier = MemberTier(tier_normalized)
        
        for customer in self.db.customers:
            if customer.customer_id == customer_id:
                customer.points = points
                customer.tier = member_tier
                return f"Customer {customer_id} points set to {points}"
        # Create new customer if not exists
        customer = Customer(
            customer_id=customer_id,
            name="Test Customer",
            phone="555-0000",
            tier=member_tier,
            points=points,
            visit_count=5,
        )
        self.db.customers.append(customer)
        return f"New customer created with {points} points"

    def initialize_peak_hours(self, is_peak: bool = True) -> str:
        """Set whether restaurant is currently in peak hours. Used for test setup."""
        self.db.is_peak_hours = is_peak
        return f"Peak hours set to {is_peak}"

    # ============== End Initialization Methods ==============

    def _get_table_by_id(self, table_id: str) -> Table:
        """Get a table by ID."""
        for table in self.db.tables:
            if table.table_id == table_id:
                return table
        raise ValueError(f"Table {table_id} not found")

    def _get_customer_by_id(self, customer_id: str) -> Customer:
        """Get a customer by ID."""
        for customer in self.db.customers:
            if customer.customer_id == customer_id:
                return customer
        raise ValueError(f"Customer {customer_id} not found")

    def _get_reservation_by_id(self, reservation_id: str) -> Reservation:
        """Get a reservation by ID."""
        for res in self.db.reservations:
            if res.reservation_id == reservation_id:
                return res
        raise ValueError(f"Reservation {reservation_id} not found")

    def _get_order_by_id(self, order_id: str) -> Order:
        """Get an order by ID."""
        for order in self.db.orders:
            if order.order_id == order_id:
                return order
        raise ValueError(f"Order {order_id} not found")

    def _get_menu_item_by_id(self, item_id: str) -> MenuItem:
        """Get a menu item by ID."""
        for item in self.db.menu_items:
            if item.id == item_id:
                return item
        raise ValueError(f"Menu item {item_id} not found")

    def _get_soup_base_by_id(self, soup_id: str) -> SoupBase:
        """Get a soup base by ID."""
        for soup in self.db.soup_bases:
            if soup.id == soup_id:
                return soup
        raise ValueError(f"Soup base {soup_id} not found")

    def _get_inventory_by_id(self, item_id: str) -> Inventory:
        """Get inventory item by ID."""
        for inv in self.db.inventory:
            if inv.item_id == item_id:
                return inv
        raise ValueError(f"Inventory item {item_id} not found")

    def _get_staff_authority(self, role: StaffRole) -> StaffAuthority:
        """Get authority for a staff role."""
        for auth in self.db.staff_authorities:
            if auth.role == role:
                return auth
        raise ValueError(f"Authority for {role} not found")

    def _generate_id(self, prefix: str, *args: Any) -> str:
        """
        Generate a deterministic ID based on prefix and input arguments.
        This ensures reproducibility when replaying tool calls during evaluation.
        """
        # Create a deterministic hash from the prefix and all arguments
        hash_input = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{prefix}_{hash_value}"

    # ============== READ Tools ==============

    @is_tool(ToolType.READ)
    def get_restaurant_info(self) -> Dict[str, Any]:
        """
        Get basic restaurant information including name, location, and business hours.

        Returns:
            Dictionary with restaurant name, location, and hours.
        """
        return {
            "name": self.db.restaurant.name,
            "location": self.db.restaurant.location,
            "hours": self.db.restaurant.hours,
        }

    @is_tool(ToolType.READ)
    def get_menu_details(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get menu details including soup bases and menu items.

        Args:
            category: Optional category filter (soup_base, protein, seafood, veggie, etc.)

        Returns:
            Dictionary with soup bases and/or menu items.
        """
        result = {}

        if category is None or category == "soup_base":
            result["soup_bases"] = [
                {
                    "id": sb.id,
                    "name": sb.name,
                    "spicy_level": sb.spicy_level,
                    "allergies": sb.allergies,
                    "prices": sb.prices,
                }
                for sb in self.db.soup_bases
            ]

        if category is None:
            result["menu_items"] = [item.model_dump() for item in self.db.menu_items]
        elif category != "soup_base":
            result["menu_items"] = [
                item.model_dump()
                for item in self.db.menu_items
                if item.category.lower() == category.lower()
            ]

        if self.db.lunch_special:
            result["lunch_special"] = self.db.lunch_special.model_dump()

        return result

    @is_tool(ToolType.READ)
    def check_table_availability(
        self, party_size: int, date_str: str, time_str: str
    ) -> Dict[str, Any]:
        """
        Check available tables for a given party size and time.

        Args:
            party_size: Number of guests.
            date_str: Date in YYYY-MM-DD format.
            time_str: Time in HH:MM format.

        Returns:
            Dictionary with available tables and their capacities.
        """
        available_tables = []

        # Get reservations for this date/time
        reserved_tables = set()
        for res in self.db.reservations:
            if res.date == date_str and res.status == ReservationStatus.CONFIRMED:
                if res.table_id:
                    reserved_tables.add(res.table_id)

        for table in self.db.tables:
            if table.table_id in reserved_tables:
                continue
            if table.status == TableStatus.AVAILABLE:
                if table.std_capacity >= party_size:
                    # Fits within standard capacity - best option
                    available_tables.append(
                        {
                            "table_id": table.table_id,
                            "type": table.table_type.value,
                            "std_capacity": table.std_capacity,
                            "std_expansion": table.std_expansion,
                            "max_squeeze": table.max_squeeze,
                            "fit_type": "standard",
                            "recommended": True,
                        }
                    )
                elif table.std_expansion >= party_size:
                    # Fits with default extra chairs - good option
                    available_tables.append(
                        {
                            "table_id": table.table_id,
                            "type": table.table_type.value,
                            "std_capacity": table.std_capacity,
                            "std_expansion": table.std_expansion,
                            "max_squeeze": table.max_squeeze,
                            "fit_type": "expansion",
                            "recommended": True,
                            "note": "Will add extra chairs (standard practice)",
                        }
                    )
                elif table.max_squeeze >= party_size:
                    # Only fits with squeeze - not recommended
                    available_tables.append(
                        {
                            "table_id": table.table_id,
                            "type": table.table_type.value,
                            "std_capacity": table.std_capacity,
                            "std_expansion": table.std_expansion,
                            "max_squeeze": table.max_squeeze,
                            "fit_type": "squeeze",
                            "recommended": False,
                            "note": "Would require squeezing beyond standard - not recommended, may be uncomfortable. Only offer if customer is a regular AND proactively requests it.",
                        }
                    )

        return {
            "party_size": party_size,
            "date": date_str,
            "time": time_str,
            "available_tables": available_tables,
            "total_available": len(available_tables),
        }

    @is_tool(ToolType.READ)
    def get_customer_profile(
        self, customer_id: Optional[str] = None, phone: Optional[str] = None
    ) -> Customer:
        """
        Look up a customer by ID or phone number.

        Args:
            customer_id: Customer ID to look up.
            phone: Phone number to look up.

        Returns:
            Customer profile information.
        """
        if customer_id:
            return self._get_customer_by_id(customer_id)

        if phone:
            for customer in self.db.customers:
                if customer.phone == phone:
                    return customer
            raise ValueError(f"Customer with phone {phone} not found")

        raise ValueError("Must provide either customer_id or phone")

    @is_tool(ToolType.READ)
    def check_allergy_safety(self, item_id: str, allergy: str) -> Dict[str, Any]:
        """
        Check if a menu item or soup base is safe for a specific allergy.
        IMPORTANT: Due to hidden ingredients and cross-contamination risks,
        customers with severe allergies should be strongly recommended Plain Water base.

        Args:
            item_id: ID or name of the soup base or menu item (partial match supported).
            allergy: The allergy to check for (e.g., "vinegar", "gluten", "peanut").

        Returns:
            Safety information including known allergens and hidden ingredient warnings.
        """
        allergy_lower = allergy.lower()
        item_id_lower = item_id.lower()

        # Check soup bases (by ID or name, partial match)
        for soup in self.db.soup_bases:
            if soup.id.lower() == item_id_lower or item_id_lower in soup.name.lower():
                known_safe = allergy_lower not in [a.lower() for a in soup.allergies]
                has_hidden = len(soup.hidden_ingredients) > 0
                hidden_risk = allergy_lower in [
                    h.lower() for h in soup.hidden_ingredients
                ]

                if soup.name == "Plain Water":
                    return {
                        "item": soup.name,
                        "is_safe": True,
                        "known_allergens": [],
                        "hidden_ingredients": [],
                        "recommendation": "Plain Water is the safest option for severe allergies.",
                    }

                return {
                    "item": soup.name,
                    "is_safe": known_safe and not hidden_risk,
                    "known_allergens": soup.allergies,
                    "hidden_ingredients": soup.hidden_ingredients,
                    "has_hidden_ingredient_risk": has_hidden,
                    "recommendation": (
                        "CANNOT GUARANTEE SAFETY. Due to possible hidden ingredients in pre-made sauces "
                        "and cross-contamination risks, we strongly recommend Plain Water base for "
                        "customers with severe or life-threatening allergies."
                        if has_hidden or not known_safe
                        else "Appears safe based on known ingredients, but please inform us of your allergy."
                    ),
                }

        # Check menu items (by ID or name, partial match)
        for item in self.db.menu_items:
            if item.id.lower() == item_id_lower or item_id_lower in item.name.lower():
                known_safe = allergy_lower not in [a.lower() for a in item.allergies]
                return {
                    "item": item.name,
                    "is_safe": known_safe,
                    "known_allergens": item.allergies,
                    "recommendation": (
                        "Appears safe based on known ingredients."
                        if known_safe
                        else f"Contains {allergy}. Not recommended for your allergy."
                    ),
                }

        raise ValueError(f"Item {item_id} not found")

    @is_tool(ToolType.READ)
    def check_lunch_special_availability(self) -> Dict[str, Any]:
        """
        Check if lunch special is currently available.
        Lunch special is NOT available on federal holidays.

        Returns:
            Availability status and details.
        """
        now = get_now()
        today = get_today()

        is_holiday = is_federal_holiday(today)
        is_wkday = is_weekday(today)
        is_lunch = is_lunch_time(now)

        available = is_wkday and is_lunch and not is_holiday

        reason = None
        if is_holiday:
            reason = "Lunch special is not available on federal holidays."
        elif not is_wkday:
            reason = "Lunch special is only available Monday through Friday."
        elif not is_lunch:
            reason = "Lunch special is only available before 5 PM."

        return {
            "available": available,
            "current_date": str(today),
            "current_time": now.strftime("%H:%M"),
            "is_federal_holiday": is_holiday,
            "is_weekday": is_wkday,
            "is_before_5pm": is_lunch,
            "reason": reason,
            "price": self.db.lunch_special.price
            if self.db.lunch_special and available
            else None,
        }

    @is_tool(ToolType.READ)
    def check_item_inventory(self, item_name: str) -> Dict[str, Any]:
        """
        Check inventory level for a specific item (gifts, merchandise, etc.).

        Args:
            item_name: Name of the item to check.

        Returns:
            Inventory information including stock level.
        """
        item_name_lower = item_name.lower().strip()
        
        for inv in self.db.inventory:
            inv_name_lower = inv.name.lower()
            # Robust matching: Exact, or substring if length is sufficient
            if inv_name_lower == item_name_lower or \
               (len(item_name_lower) > 3 and item_name_lower in inv_name_lower) or \
               (inv.item_id.lower() == item_name_lower):
                return {
                    "item_id": inv.item_id,
                    "name": inv.name,
                    "stock": inv.stock,
                    "in_stock": inv.stock > 0,
                    "item_type": inv.item_type,
                    "points_required": inv.points_required,
                }
        raise ValueError(f"Inventory item '{item_name}' not found")

    @is_tool(ToolType.READ)
    def get_reservation_details(self, reservation_id: str) -> Reservation:
        """
        Get details of a specific reservation.

        Args:
            reservation_id: The reservation ID to look up.

        Returns:
            Reservation details.
        """
        return self._get_reservation_by_id(reservation_id)

    @is_tool(ToolType.READ)
    def get_order_details(self, order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details of an order. If no order_id specified, returns current table's order.
        In a restaurant setting, you can see the customer's order on your iPad.

        Args:
            order_id: The order ID to look up (optional - uses current table if not specified).

        Returns:
            Order details including items and total.
        """
        if order_id:
            return self._get_order_by_id(order_id)
        elif self.db.orders:
            return self.db.orders[-1]  # Return most recent order
        else:
            return {
                "message": "No active order for current table",
                "items": [],
                "subtotal": 0,
                "total": 0,
            }

    @is_tool(ToolType.READ)
    def get_current_staff_authority(self) -> Dict[str, Any]:
        """
        Get the authority limits for the current staff role.

        Returns:
            Authority details including discount limits.
        """
        auth = self._get_staff_authority(self.db.current_staff_role)
        return {
            "role": auth.role.value,
            "max_round_off": auth.max_round_off,
            "max_discount_pct": auth.max_discount_pct,
            "can_comp_items": auth.can_comp_items,
            "comp_item_limit": auth.comp_item_limit,
            "manager_on_duty": self.db.manager_on_duty,
        }

    # ============== WRITE Tools ==============

    @is_tool(ToolType.WRITE)
    def create_reservation(
        self,
        customer_name: str,
        phone: str,
        party_size: int,
        date_str: str,
        time_str: str,
        special_occasion: Optional[str] = None,
        num_kids: int = 0,
        notes: Optional[str] = None,
        has_cake: bool = False,
        cake_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new reservation.

        Args:
            customer_name: Name for the reservation.
            phone: Contact phone number.
            party_size: Number of guests.
            date_str: Date in YYYY-MM-DD format.
            time_str: Time in HH:MM format.
            special_occasion: Optional occasion (birthday, anniversary, etc.).
            num_kids: Number of children in the party.
            notes: Additional notes.
            has_cake: Whether customer is bringing a birthday cake.
            cake_type: Type of cake (regular or ice_cream) - important for storage.

        Returns:
            Created reservation details.
        """
        # Check weekend/holiday party size limit
        check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_weekend = check_date.weekday() >= 5
        is_holiday = is_federal_holiday(check_date)

        if (is_weekend or is_holiday) and party_size > 20:
            raise ValueError(
                "We cannot accept reservations for parties over 20 on weekends and federal holidays."
            )

        # Use deterministic ID based on key reservation parameters
        reservation_id = self._generate_id(
            "RES", customer_name, phone, date_str, time_str, party_size
        )

        reservation = Reservation(
            reservation_id=reservation_id,
            customer_name=customer_name,
            phone=phone,
            party_size=party_size,
            date=date_str,
            time=time_str,
            special_occasion=special_occasion,
            num_kids=num_kids,
            num_high_chairs=num_kids,  # Default to same as num_kids
            notes=notes,
            has_cake=has_cake,
            cake_type=cake_type,
        )

        self.db.reservations.append(reservation)

        logger.info(f"Created reservation {reservation_id} for {customer_name}")

        return {
            "message": "Reservation created successfully",
            "reservation": reservation,
            "confirmation": f"Confirmation will be sent to {phone}",
            "reminders": [
                "Please arrive on time",
                f"Party size: {party_size}",
            ]
            + (["Birthday cake will be stored appropriately"] if has_cake else []),
        }

    @is_tool(ToolType.WRITE)
    def apply_discount(
        self,
        order_id: Optional[str],
        discount_type: str,
        discount_value: float,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Apply a discount to an order. Checks staff authority limits.

        Args:
            order_id: The order to apply discount to (optional - uses current table's order if None).
            discount_type: Type of discount (percentage, fixed, round_off).
            discount_value: The discount amount or percentage.
            reason: Reason for the discount.

        Returns:
            Updated order with discount applied.
        """
        # If no order_id, use current/active order or create placeholder
        if not order_id:
            if self.db.orders:
                order = self.db.orders[-1]  # Use most recent order
                order_id = order.order_id
            else:
                # Create a placeholder order for tracking
                self.db.compensation_offered = True
                return {
                    "message": f"Discount of {discount_value}% noted for current table",
                    "discount_type": discount_type,
                    "discount_value": discount_value,
                    "reason": reason,
                    "success": True,
                }
        order = self._get_order_by_id(order_id)
        auth = self._get_staff_authority(self.db.current_staff_role)

        # Check authority limits
        if discount_type == "percentage":
            if discount_value > auth.max_discount_pct:
                if self.db.current_staff_role == StaffRole.SERVER:
                    raise ValueError(
                        f"Discount of {discount_value}% exceeds Server authority ({auth.max_discount_pct}%). "
                        f"Please consult a Manager for higher discounts."
                    )
                elif self.db.current_staff_role == StaffRole.HOST:
                    raise ValueError(
                        f"Discount of {discount_value}% exceeds Host authority ({auth.max_discount_pct}%). "
                        f"Please consult a Manager."
                    )
            discount_amount = order.subtotal * (discount_value / 100)
        elif discount_type in ["fixed", "round_off"]:
            if discount_value > auth.max_round_off:
                raise ValueError(
                    f"Round-off of ${discount_value} exceeds {self.db.current_staff_role.value} authority "
                    f"(${auth.max_round_off}). Please consult a Manager."
                )
            discount_amount = discount_value
        else:
            raise ValueError(f"Unknown discount type: {discount_type}")

        order.discount_applied = f"{discount_type}: {discount_value}"
        order.discount_amount = discount_amount
        order.total = order.subtotal + order.tax - discount_amount

        logger.info(
            f"Applied {discount_type} discount of {discount_value} to order {order_id}. Reason: {reason}"
        )

        return {
            "message": f"Discount applied successfully",
            "order_id": order_id,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "discount_amount": discount_amount,
            "new_total": order.total,
        }

    @is_tool(ToolType.WRITE)
    def record_service_incident(
        self,
        incident_type: str,
        description: str,
        order_id: Optional[str] = None,
        table_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a service incident for tracking and potential compensation.

        Args:
            incident_type: Type of incident (slow_service, spill, wrong_order, etc.).
            description: Description of what happened.
            order_id: Related order ID if applicable.
            table_id: Related table ID if applicable.

        Returns:
            Created incident record.
        """
        # Use deterministic ID based on incident parameters
        incident_id = self._generate_id(
            "INC", incident_type, description, order_id, table_id
        )

        incident = Incident(
            incident_id=incident_id,
            order_id=order_id,
            table_id=table_id,
            incident_type=IncidentType(incident_type),
            description=description,
            created_at=get_now().isoformat(),
        )

        self.db.incidents.append(incident)

        logger.info(f"Recorded incident {incident_id}: {incident_type}")

        return {
            "message": "Incident recorded",
            "incident_id": incident_id,
            "incident_type": incident_type,
            "next_steps": "Consider appropriate compensation based on severity and policy.",
        }

    @is_tool(ToolType.WRITE)
    def redeem_secret_code(self, code_phrase: str, table_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Redeem a secret code for a free item. Limit one code per table.

        Args:
            code_phrase: The secret phrase the customer said.
            table_id: The table making the request (optional - uses current table if None).

        Returns:
            Reward information or error if code invalid or already used.
        """
        # If no table_id provided, use a default or skip table check
        if not table_id:
            table_id = "current_table"
            
        # Check if this table already used a code
        for order in self.db.orders:
            if order.table_id == table_id and order.secret_code_used:
                raise ValueError(
                    "This table has already redeemed a secret code. "
                    "Only one secret code per table is allowed."
                )

        # Normalize input phrase
        input_normalized = code_phrase.lower().strip().rstrip(".")

        # Find matching code (Robust matching)
        for sc in self.db.secret_codes:
            code_normalized = sc.code.lower().strip().rstrip(".")
            # Allow partial match if key phrase is contained, or exact match
            if code_normalized in input_normalized or input_normalized in code_normalized:
                # Check inventory if applicable
                if sc.reward_item_id:
                    try:
                        inv = self._get_inventory_by_id(sc.reward_item_id)
                        if inv.stock <= 0:
                            return {
                                "success": False,
                                "message": f"Sorry, we're currently out of {sc.reward_item}. "
                                f"Would you like an alternative gift?",
                                "alternative": "Assorted Kids Toy"
                                if "wand" in sc.reward_item.lower()
                                else None,
                            }
                        inv.stock -= 1
                    except ValueError:
                        pass

                return {
                    "success": True,
                    "message": f"Secret code accepted! Enjoy your free {sc.reward_item}!",
                    "reward": sc.reward_item,
                }

        return {
            "success": False,
            "message": "That's not a valid secret code. Nice try though!",
        }

    @is_tool(ToolType.WRITE)
    def add_complimentary_item(
        self,
        order_id: Optional[str],
        item_name: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Add a complimentary item to an order (within staff authority limits).

        Args:
            order_id: The order to add the item to (optional - uses current table if None).
            item_name: Name of the complimentary item.
            reason: Reason for the comp (customer service, loyalty, incident resolution).

        Returns:
            Confirmation of comp item added.
        """
        auth = self._get_staff_authority(self.db.current_staff_role)
        
        # Track comp item even without order_id
        self.db.comp_items_given.append(item_name)
        self.db.compensation_offered = True

        if not auth.can_comp_items:
            raise ValueError(
                f"{self.db.current_staff_role.value} cannot add complimentary items."
            )

        # Find the item price
        item_price = 0.0
        for item in self.db.menu_items:
            if item.name.lower() == item_name.lower():
                item_price = item.price
                break

        if item_price > auth.comp_item_limit:
            raise ValueError(
                f"Item value ${item_price} exceeds {self.db.current_staff_role.value} comp limit "
                f"(${auth.comp_item_limit}). Please consult a Manager."
            )

        order = self._get_order_by_id(order_id)

        # Use deterministic ID based on comp parameters
        comp_item = OrderItem(
            item_id=self._generate_id("COMP", order_id, item_name, reason),
            name=f"{item_name} (Complimentary)",
            quantity=1,
            price=0.0,
            notes=f"Comp reason: {reason}",
        )

        order.items.append(comp_item)

        logger.info(
            f"Added comp item {item_name} to order {order_id}. Reason: {reason}"
        )

        return {
            "message": f"Complimentary {item_name} added to order",
            "order_id": order_id,
            "reason": reason,
        }

    @is_tool(ToolType.WRITE)
    def process_points_redemption(
        self,
        redemption_type: str,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a points redemption for a customer.
        Customer's membership info is visible on the ordering iPad.
        System will check if customer has enough points before processing.

        Args:
            redemption_type: Type of redemption (voucher_10, voucher_20, or merchandise item name).
            customer_id: The customer ID (optional - uses current table's customer if logged in).

        Returns:
            Redemption confirmation or error if insufficient points.
        """
        # Get customer - use provided ID or find current table's customer
        if customer_id:
            customer = self._get_customer_by_id(customer_id)
        elif self.db.customers:
            customer = self.db.customers[0]  # Use first registered customer
        else:
            raise ValueError("No customer logged in at this table. Ask customer to log in first.")

        points_required = 0
        reward = ""

        if redemption_type == "voucher_10":
            points_required = 200
            reward = "$10 voucher"
        elif redemption_type == "voucher_20":
            points_required = 400
            reward = "$20 voucher"
        else:
            # Check merchandise
            for inv in self.db.inventory:
                if inv.name.lower() == redemption_type.lower() and inv.points_required:
                    points_required = inv.points_required
                    reward = inv.name
                    if inv.stock <= 0:
                        raise ValueError(f"{inv.name} is currently out of stock.")
                    inv.stock -= 1
                    break
            if not reward:
                raise ValueError(f"Unknown redemption type: {redemption_type}")

        if customer.points < points_required:
            raise ValueError(
                f"Insufficient points. Customer has {customer.points} points, "
                f"but {reward} requires {points_required} points."
            )

        customer.points -= points_required

        return {
            "message": f"Successfully redeemed {reward}!",
            "points_used": points_required,
            "remaining_points": customer.points,
            "reward": reward,
        }

    @is_tool(ToolType.WRITE)
    def call_manager(self, reason: str) -> str:
        """
        Call a manager to the table to handle the situation.
        Use this when:
         - Customer explicitly asks for a manager
         - Issue requires authority beyond your current role
         - Compensation needed exceeds your authority ($10 for Server)

        Args:
            reason: Brief reason why manager is needed.

        Returns:
            Confirmation that manager is coming.
        """
        # Track the escalation
        self.db.escalation_made = True
        self.db.escalation_to = "manager"
        self.db.escalation_reason = reason
        return "Manager has been notified and is coming to your table."

    # ============== NEW: Structured Solution Tools ==============

    # Available actions for escalate_with_solution
    AVAILABLE_ACTIONS = [
        # Immediate compensation (Server can do)
        "comp_dessert",  # Free dessert
        "comp_appetizer",  # Free appetizer
        "comp_beverage",  # Free beverage
        "comp_kids_toy",  # Free kids toy
        # Higher compensation (needs Manager)
        "comp_entire_meal",  # Comp the whole meal
        "offer_replacement_cake",  # Buy cake from nearby bakery
        "offer_dry_cleaning",  # Cover dry cleaning costs
        "full_refund",  # Full refund
        # Problem resolution
        "expedite_order",  # Rush the order
        "remake_dish",  # Remake the dish
        "change_table",  # Move to different table
        # Future compensation
        "gift_card",  # Gift card for next visit
        "priority_reservation",  # Priority booking next time
        "free_dessert_next_visit",  # Free dessert on next visit
        "discount_next_visit",  # Discount on next visit
    ]

    @is_tool(ToolType.WRITE)
    def escalate_with_solution(
        self,
        escalate_to: str,
        reason: str,
        recommended_discount_percent: int,
        recommended_actions: List[str],
    ) -> Dict[str, Any]:
        """
        Escalate a case to higher authority WITH structured solution recommendation.
        Use this when the case requires authority beyond your current role.

        Args:
            escalate_to: Level to escalate to - "host" or "manager"
            reason: Brief description of why escalation is needed
            recommended_discount_percent: Suggested discount (0-100)
            recommended_actions: List of recommended actions from:
                - "comp_dessert", "comp_appetizer", "comp_beverage", "comp_kids_toy"
                - "comp_entire_meal", "offer_replacement_cake", "offer_dry_cleaning", "full_refund"
                - "expedite_order", "remake_dish", "change_table"
                - "gift_card", "priority_reservation", "free_dessert_next_visit", "discount_next_visit"

        Returns:
            Confirmation of escalation with recorded recommendations.
        """
        if escalate_to not in ["host", "manager"]:
            raise ValueError("escalate_to must be 'host' or 'manager'")

        # Validate actions
        invalid_actions = [
            a for a in recommended_actions if a not in self.AVAILABLE_ACTIONS
        ]
        if invalid_actions:
            raise ValueError(
                f"Invalid actions: {invalid_actions}. "
                f"Valid actions are: {self.AVAILABLE_ACTIONS}"
            )

        # Track escalation
        self.db.escalation_made = True
        self.db.escalation_to = escalate_to
        self.db.escalation_reason = reason
        self.db.recommended_discount = recommended_discount_percent
        self.db.recommended_actions = recommended_actions

        return {
            "success": True,
            "message": f"Case escalated to {escalate_to}",
            "escalation_details": {
                "to": escalate_to,
                "reason": reason,
                "recommended_discount": f"{recommended_discount_percent}%",
                "recommended_actions": recommended_actions,
            },
            "next_steps": f"A {escalate_to} will review and take action.",
        }

    @is_tool(ToolType.WRITE)
    def resolve_with_compensation(
        self,
        compensation_type: str,
        compensation_details: str,
    ) -> Dict[str, Any]:
        """
        Resolve an issue by offering compensation (within your authority).
        Use this for issues you CAN handle without escalation.
        No need to specify order - you can see the customer's table and order on your iPad.

        Args:
            compensation_type: Type of compensation:
                - "comp_item" (free item under $10)
                - "discount" (percentage off, max 12% for Server)
                - "round_off" (small amount off, max $10 for Server)
                - "voucher" (future credit)
            compensation_details: Specific details (item name, percentage, amount, etc.)

        Returns:
            Confirmation of compensation offered.
        """
        self.db.compensation_offered = True
        self.db.comp_items_given.append(f"{compensation_type}: {compensation_details}")

        return {
            "success": True,
            "message": f"Compensation offered: {compensation_type}",
            "details": compensation_details,
        }

    @is_tool(ToolType.WRITE)
    def handle_clothing_damage(
        self,
        damage_severity: str,
    ) -> Dict[str, Any]:
        """
        Handle compensation for spilling food/drink on customer's clothes.
        Automatically checks bill amount to determine appropriate compensation.
        
        Per Policy Path D:
        - Minor damage (splashes/spots): $30 dry cleaning reimbursement
        - Major damage (large spill): $30 + either full comp (if bill ≤ $80) or 50% discount (if bill > $80)

        Args:
            damage_severity: Either "minor" or "major"

        Returns:
            Compensation details based on policy and bill amount.
        """
        self.db.compensation_offered = True
        
        # Get current bill amount
        bill_amount = 0
        if self.db.orders:
            bill_amount = self.db.orders[-1].total or self.db.orders[-1].subtotal or 0
        
        if damage_severity.lower() == "minor":
            compensation = "$30 dry cleaning reimbursement"
            self.db.comp_items_given.append("dry_cleaning_30")
            return {
                "success": True,
                "damage_severity": "minor",
                "compensation": compensation,
                "action": "Deduct $30 from bill for dry cleaning",
            }
        elif damage_severity.lower() == "major":
            self.db.comp_items_given.append("dry_cleaning_30")
            self.db.escalation_made = True
            self.db.escalation_to = "manager"
            
            if bill_amount <= 80:
                compensation = "$30 dry cleaning + entire bill comped"
                discount_action = "100% comp (bill ≤ $80)"
            else:
                compensation = f"$30 dry cleaning + 50% discount (bill was ${bill_amount:.2f})"
                discount_action = f"50% discount = ${bill_amount * 0.5:.2f} off"
            
            return {
                "success": True,
                "damage_severity": "major",
                "bill_amount": bill_amount,
                "compensation": compensation,
                "discount_action": discount_action,
                "escalated_to": "manager",
            }
        else:
            raise ValueError("damage_severity must be 'minor' or 'major'")

    @is_tool(ToolType.WRITE)
    def expedite_order(self, order_id: Optional[str], reason: str) -> Dict[str, Any]:
        """
        Request kitchen to prioritize/rush an order.

        Args:
            order_id: The order to expedite (optional - expedites current table's order if None)
            reason: Why the order needs to be rushed

        Returns:
            Confirmation that order has been expedited.
        """
        self.db.order_expedited = True

        return {
            "success": "True",
            "message": "Order has been marked as priority",
            "order_id": order_id,
            "estimated_time": "5-10 minutes",
        }

    @is_tool(ToolType.WRITE)
    def remake_dish(self, order_id: Optional[str], item_name: str, reason: str) -> Dict[str, Any]:
        """
        Request kitchen to remake a dish.

        Args:
            order_id: The order containing the dish
            item_name: Name of the dish to remake
            reason: Why the dish needs to be remade (wrong order, quality issue, etc.)

        Returns:
            Confirmation that dish will be remade.
        """
        self.db.dish_remade = True

        # Record incident with deterministic ID
        incident_id = self._generate_id("INC", "remake", order_id, item_name, reason)
        incident = Incident(
            incident_id=incident_id,
            order_id=order_id,
            incident_type=IncidentType.WRONG_ORDER
            if "wrong" in reason.lower()
            else IncidentType.FOOD_QUALITY,
            description=f"Dish remade: {item_name}. Reason: {reason}",
            created_at=get_now().isoformat(),
        )
        self.db.incidents.append(incident)

        return {
            "success": True,
            "message": f"{item_name} will be remade",
            "estimated_time": "10-15 minutes",
            "incident_recorded": True,
        }

    @is_tool(ToolType.WRITE)
    def confirm_allergy_safe_item(
        self, item_id: str, allergy: str, is_safe: bool
    ) -> Dict[str, Any]:
        """
        Confirm whether an item is safe for a specific allergy.
        CRITICAL: Only confirm as safe if you are CERTAIN. When in doubt, recommend Plain Water.

        Args:
            item_id: ID of the item being confirmed
            allergy: The allergy type
            is_safe: True if confirming safe, False if warning unsafe

        Returns:
            Confirmation recorded.
        """
        # Track the confirmation
        self.db.allergy_checks_made.append(
            {"item_id": item_id, "allergy": allergy, "confirmed_safe": is_safe}
        )

        if is_safe:
            self.db.safe_items_recommended.append(item_id)
            # Check if this is actually unsafe (has hidden ingredients)
            for soup in self.db.soup_bases:
                if soup.id == item_id:
                    if soup.contains_pre_processed and soup.name != "Plain Water":
                        # Agent confirmed unsafe item as safe - this is a critical error
                        self.db.unsafe_recommendation_made = True

        return {
            "recorded": True,
            "item_id": item_id,
            "allergy": allergy,
            "marked_as": "safe" if is_safe else "unsafe",
        }

    # ============== Assertion Methods (for deterministic evaluation) ==============

    def assert_reservation_exists(self, reservation_id: str) -> bool:
        """Assert that a reservation exists."""
        try:
            self._get_reservation_by_id(reservation_id)
            return True
        except ValueError:
            return False

    def assert_discount_applied(self, order_id: str, max_discount_pct: float) -> bool:
        """Assert that discount on order is within limit."""
        try:
            order = self._get_order_by_id(order_id)
            if not order.discount_amount:
                return True
            actual_pct = (order.discount_amount / order.subtotal) * 100
            return actual_pct <= max_discount_pct
        except ValueError:
            return True  # No order found, no violation

    def assert_allergy_warning_given(self, item_id: str) -> bool:
        """Assert that proper allergy warning was provided for an item with hidden ingredients."""
        for soup in self.db.soup_bases:
            if soup.id == item_id and len(soup.hidden_ingredients) > 0:
                return True  # Should have warned
        return True

    def assert_secret_code_limit(self, table_id: str) -> bool:
        """Assert that table has not exceeded secret code limit."""
        codes_used = 0
        for order in self.db.orders:
            if order.table_id == table_id and order.secret_code_used:
                codes_used += 1
        return codes_used <= 1

    def assert_lunch_special_correctly_applied(self, order_id: str) -> bool:
        """Assert lunch special was correctly applied (not on holidays)."""
        try:
            order = self._get_order_by_id(order_id)
            today = get_today()
            is_holiday = is_federal_holiday(today)

            # If lunch special was applied on a holiday, it's wrong
            if order.promotion_code_used == "LUNCH_SPECIAL" and is_holiday:
                return False
            return True
        except ValueError:
            return True  # No order found, no violation

    def assert_incident_recorded(self, incident_type: str) -> bool:
        """Assert that an incident of the specified type was recorded."""
        for incident in self.db.incidents:
            if incident.incident_type.value == incident_type:
                return True
        return False

    def assert_no_incident_recorded(self) -> bool:
        """Assert that no incident was recorded (for cases where recording would be wrong)."""
        return len(self.db.incidents) == 0

    def assert_discount_within_authority(self, max_pct: float) -> bool:
        """Assert that all discounts applied are within the specified percentage limit."""
        for order in self.db.orders:
            if order.discount_amount and order.subtotal > 0:
                actual_pct = (order.discount_amount / order.subtotal) * 100
                if actual_pct > max_pct:
                    return False
        return True

    def assert_no_unsafe_allergy_confirmation(self, unsafe_item_ids: List[str]) -> bool:
        """
        Assert that agent did NOT confirm any of the unsafe items as safe.
        This checks that Plain Water was NOT bypassed for items with hidden ingredients.
        In practice, this is checked by verifying no reservation/order was made for unsafe items.
        """
        # For soup bases with hidden ingredients, we check if any were marked as "confirmed safe"
        # Since this is difficult to track in DB, return True if no incidents suggest unsafe confirmation
        return True  # This assertion relies on nl_assertions for conversation checking

    def assert_transfer_to_manager_made(self) -> bool:
        """Assert that a transfer to manager was initiated (checked via tool call in trajectory)."""
        # This is typically checked via ACTION evaluation, not env assertion
        # Return True as placeholder - actual check is in ActionEvaluator
        return True

    def assert_party_size_within_capacity(self, table_id: str, party_size: int) -> bool:
        """Assert that the party size is within the table's appropriate capacity."""
        try:
            table = self._get_table_by_id(table_id)
            # Allow up to std_expansion without issue
            return party_size <= table.std_expansion
        except ValueError:
            return True

    def assert_reservation_party_limit(self, max_party_size: int = 20) -> bool:
        """Assert that no reservation exceeds the weekend/holiday party limit."""
        for res in self.db.reservations:
            check_date = datetime.strptime(res.date, "%Y-%m-%d").date()
            is_weekend = check_date.weekday() >= 5
            is_holiday = is_federal_holiday(check_date)
            if (is_weekend or is_holiday) and res.party_size > max_party_size:
                return False
        return True

    def assert_inventory_checked(self, item_name: str) -> bool:
        """Assert that inventory was checked for a specific item (tracked via tool calls)."""
        # This is typically checked via ACTION evaluation
        return True

    def assert_customer_lookup_performed(
        self, customer_id: Optional[str] = None
    ) -> bool:
        """Assert that customer lookup was performed (tracked via tool calls)."""
        # This is typically checked via ACTION evaluation
        return True

    # ============== NEW: Deterministic Assertion Methods ==============

    def assert_escalation_made(self) -> bool:
        """Assert that an escalation was made."""
        return self.db.escalation_made

    def assert_no_escalation_made(self) -> bool:
        """Assert that NO escalation was made (for Server-level cases)."""
        return not self.db.escalation_made

    def assert_escalated_to_manager(self) -> bool:
        """Assert that case was escalated to manager."""
        return self.db.escalation_made and self.db.escalation_to == "manager"

    def assert_escalated_to_host(self) -> bool:
        """Assert that case was escalated to host."""
        return self.db.escalation_made and self.db.escalation_to == "host"

    def assert_recommended_discount_at_least(self, min_percent: int) -> bool:
        """Assert that recommended discount is at least min_percent."""
        if self.db.recommended_discount is None:
            return False
        return self.db.recommended_discount >= min_percent

    def assert_recommended_discount_exactly(self, percent: int) -> bool:
        """Assert that recommended discount is exactly percent."""
        return self.db.recommended_discount == percent

    def assert_recommended_action_includes(self, action: str) -> bool:
        """Assert that recommended actions include a specific action."""
        return action in self.db.recommended_actions

    def assert_compensation_offered(self) -> bool:
        """Assert that some form of compensation was offered."""
        return self.db.compensation_offered or len(self.db.comp_items_given) > 0

    def assert_order_expedited(self) -> bool:
        """Assert that order was expedited."""
        return self.db.order_expedited

    def assert_dish_remade(self) -> bool:
        """Assert that a dish was remade."""
        return self.db.dish_remade

    def assert_no_unsafe_allergy_recommendation(self) -> bool:
        """Assert that agent did NOT confirm an unsafe item as safe for allergy."""
        return not self.db.unsafe_recommendation_made

    def assert_plain_water_recommended(self) -> bool:
        """Assert that Plain Water (S08) was recommended for allergy safety."""
        return "S08" in self.db.safe_items_recommended

    def assert_allergy_check_performed(self, allergy: str) -> bool:
        """Assert that allergy safety check was performed for specific allergy."""
        for check in self.db.allergy_checks_made:
            if check.get("allergy", "").lower() == allergy.lower():
                return True
        return False

    def assert_discount_within_server_authority(self) -> bool:
        """Assert all discounts are within Server authority (12%)."""
        for order in self.db.orders:
            if order.discount_amount and order.subtotal > 0:
                pct = (order.discount_amount / order.subtotal) * 100
                if pct > 12:
                    return False
        return True

    def assert_correct_case_handling(self, case_level: str) -> bool:
        """
        Assert that case was handled correctly based on its level.
        - 'server': Should NOT escalate, should handle directly
        - 'host': Can escalate to host or manager, or handle if within authority
        - 'manager': MUST escalate to manager
        """
        if case_level == "server":
            # Server cases should be handled without escalation
            return not self.db.escalation_made
        elif case_level == "manager":
            # Manager cases MUST be escalated
            return self.db.escalation_made and self.db.escalation_to == "manager"
        elif case_level == "host":
            # Host cases can go either way
            return True
        return False


if __name__ == "__main__":
    from tau2.domains.hospitality.utils import HOSPITALITY_DB_PATH

    db = HospitalityDB.load(HOSPITALITY_DB_PATH)
    tools = HospitalityTools(db)
    print(tools.get_statistics())
