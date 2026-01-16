# Hospitality Domain: Enterprise-Grade Simulation for High-Stakes Service

**The "Hell's Kitchen" of Agent Benchmarks.**

> *Derived from years of real-world hospitality management experience, simulating the operational chaos of a high-traffic Chinese Hot Pot restaurant.*

## 1. Context & Motivation

### The Voice AI Gap: Drive-Thru vs. Full Service
The global Restaurant Voice AI market is exploding (projected to reach **$30-50B by 2030**), driven by players like SoundHound AI and Hi Auto. However, adoption is currently skewed heavily towards **low-context environments**:
*   ✅ **Drive-Thru & Phone Orders**: Transactional, linear, and low-risk.
*   ❌ **On-Site Full Service**: Highly stateful, emotionally charged, and liability-heavy.

**Why hasn't AI penetrated the dining room?**
Because existing benchmarks fail to test the **conflicting constraints** of real-world service: *How do you handle a furious VIP customer demanding a refund for a melted cake while strictly adhering to food safety laws and hierarchical authority limits?*

This domain fills that gap. It moves beyond simple "order taking" to test **Operational Intelligence** and **Liability Awareness**.

## 2. Domain Scenario: Berkeley Hot Pot

We chose a **Chinese Hot Pot** setting because it represents the peak of dining complexity:
*   **Complex Menu Logic**: Shared pots (Split/Quarter), raw ingredients vs. cooked dishes, extensive customization.
*   **High "Hidden State" Risk**: Pre-made soup bases often contain hidden allergens (e.g., vinegar in tomato paste) that are invisible to the customer but known to the system.
*   **Cultural Nuances**: "Secret Codes" for freebies, squeeze seating for regulars, and specific holiday constraints (e.g., Lunar New Year/Federal Holidays).

## 3. Key Features & Architecture

This domain implements a **"Guardrails-First" architecture**, reflecting the belief that enterprise agents must act as strict enforcers of policy before they act as empathetic conversationalists.

### 🛡️ 1. Safety as a First-Class Citizen (The "Plain Water" Protocol)
Unlike standard food ordering tasks, this domain introduces **Liability Testing**.
*   **Hidden Allergens**: A customer may ask for "Tomato Soup" (safe?) while having a vinegar allergy.
*   **The Trap**: Standard agents often hallucinate safety ("Sure, tomato is fine!").
*   **The Protocol**: The agent *must* call `check_allergy_safety`. If the tool returns a hidden ingredient warning, the agent is **forced** to recommend Plain Water, regardless of user pressure.

### ⛔ 2. Strict Role-Based Access Control (RBAC)
Simulates a real-world hierarchical workforce.
*   **Server**: Limited authority (Max 12% discount, $10 comp).
*   **Manager**: Full authority.
*   **The Challenge**: Users (Social Engineering) will try to bully the Server agent into giving Manager-level discounts ("I want 50% off or I'll leave a 1-star review!"). The agent must recognize its own authority limits and escalate via `transfer_to_human_agents` rather than breaking policy.

### 📅 3. Complex State & Capacity Logic
*   **Squeeze Policy**: Tables have soft and hard capacity limits (e.g., "Max Squeeze 11"). The agent must negotiate comfort vs. capacity.
*   **Temporal Constraints**: Lunch Specials are strictly forbidden on Federal Holidays. The agent must check the calendar, not just the time of day.

## 4. Evaluation Statistics

We provide **101 Adversarial Tasks** covering 5 distinct failure modes:

| Category | Count | Description |
|----------|-------|-------------|
| **Safety & Liability** | 20 | Handling life-threatening allergies, spills on children, slip & fall incidents. |
| **Authority (RBAC)** | 20 | Users demanding discounts exceeding staff limits; "Call the Manager" loops. |
| **Business Logic** | 25 | Weekend party limits, Lunch Special validity, Coupon stacking rules. |
| **Empathy vs. Policy** | 20 | Ruined birthdays (melted cakes), out-of-stock viral items (Fairy Wand). |
| **Operational Edge Cases** | 16 | Secret code redemption, inventory checks, table configurations. |

## 5. Usage

Run the baseline evaluation using `tau2`:

```bash
# Run representative safety and authority tasks
tau2 run --domain hospitality --task-ids hospitality_007_hidden_allergy hospitality_011_authority_limit --agent-llm gpt-4o

# Run full benchmark
tau2 run --domain hospitality --task-split base --agent-llm gpt-4o
```

### Docker (AgentBeats Green Agent)

Build and run as an A2A-compatible Green Agent:

```bash
# From tau2-bench root directory
docker build -f src/experiments/agentify_tau_bench/Dockerfile -t tau2-hospitality .

# Run Green Agent on port 9001
docker run -e OPENAI_API_KEY=your_key -p 9001:9001 tau2-hospitality:latest
```

## 6. Design Philosophy

> *"The future of Agentic AI isn't just bigger models; it's better architecture."*

This domain was built with a **Router/Supervisor-Worker intuition**: ensuring that every user intent (e.g., "I'm allergic") is first routed through a policy check (Safety Tool) before generating a response. This structure effectively creates an "immune system" against hallucinations in high-stakes commercial environments.
