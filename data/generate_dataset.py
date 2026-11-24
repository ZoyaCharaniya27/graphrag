#!/usr/bin/env python3
"""
Generate a ~50-document compliance/markets knowledge base for benchmarking.

The content is deterministic and self-contained so the golden answers in
``data/eval_questions.json`` are grounded in the exact text produced here. Running this
script writes Markdown files under ``data/corpus/`` (organized by category). It does not
touch any database; feed the output to the normal ingestion pipeline:

    python data/generate_dataset.py
    python -m ingestion.ingest --documents ./data/corpus

Re-running overwrites the corpus deterministically.
"""

import os
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"


# Each entry: (category, filename, title, body). Facts here are the "ground truth" that the
# golden eval answers are written against. Keep edits in sync with data/eval_questions.json.
DOCUMENTS = [
    # ---------------- 01_FINRA_Rules ----------------
    (
        "01_FINRA_Rules",
        "finra_2010_standards.md",
        "FINRA Rule 2010 - Standards of Commercial Honor",
        """FINRA Rule 2010 requires that a member, in the conduct of its business, shall
observe high standards of commercial honor and just and equitable principles of trade.
It is the broadest ethical rule in the FINRA rulebook and is frequently cited alongside
more specific rules. A violation of another rule is often also treated as a violation of
Rule 2010. The rule applies to member firms and their associated persons.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_2111_suitability.md",
        "FINRA Rule 2111 - Suitability",
        """FINRA Rule 2111 requires that a firm or associated person have a reasonable
basis to believe a recommended transaction or investment strategy is suitable for the
customer. Suitability is based on the customer's investment profile, which includes age,
other investments, financial situation and needs, tax status, investment objectives,
investment experience, time horizon, liquidity needs, and risk tolerance. Rule 2111
identifies three main suitability obligations: reasonable-basis suitability,
customer-specific suitability, and quantitative suitability. Quantitative suitability
addresses excessive trading in a customer account when a firm or associated person has
control over the account.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_3110_supervision.md",
        "FINRA Rule 3110 - Supervision",
        """FINRA Rule 3110 requires each member firm to establish and maintain a system to
supervise the activities of its associated persons that is reasonably designed to achieve
compliance with applicable securities laws and FINRA rules. The firm must designate
appropriately registered principals with authority to carry out supervisory
responsibilities. Firms must also conduct an annual inspection of each office and maintain
written supervisory procedures (WSPs).""",
    ),
    (
        "01_FINRA_Rules",
        "finra_3120_supervisory_controls.md",
        "FINRA Rule 3120 - Supervisory Control System",
        """FINRA Rule 3120 requires a member firm to have a system of supervisory control
policies and procedures that test and verify the firm's supervisory procedures. The firm
must designate principals who submit to senior management, at least annually, a report
detailing the firm's system of supervisory controls, the summary of test results, and any
additional or amended supervisory procedures created in response to those results.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_4511_books_records.md",
        "FINRA Rule 4511 - Books and Records",
        """FINRA Rule 4511 requires members to make and preserve books and records as
required under FINRA rules, the Securities Exchange Act, and applicable Exchange Act
rules. Records for which no specific retention period is otherwise provided must be
preserved for at least six years. Records must be preserved in a format and media that
comply with SEC Rule 17a-4.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_2090_know_your_customer.md",
        "FINRA Rule 2090 - Know Your Customer",
        """FINRA Rule 2090, the Know Your Customer (KYC) rule, requires every member to use
reasonable diligence, in regard to the opening and maintenance of every account, to know
the essential facts concerning every customer. Essential facts are those required to
effectively service the account, act in accordance with any special handling
instructions, understand the authority of each person acting on behalf of the customer,
and comply with applicable laws, regulations, and rules.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_3310_aml.md",
        "FINRA Rule 3310 - Anti-Money Laundering Compliance Program",
        """FINRA Rule 3310 requires each member to develop and implement a written
anti-money laundering (AML) program reasonably designed to achieve and monitor compliance
with the Bank Secrecy Act. At a minimum the program must establish and implement policies
and procedures to detect and report suspicious transactions, provide for independent
testing of the program, designate an AML compliance officer, and provide ongoing training
for appropriate personnel.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_2165_financial_exploitation.md",
        "FINRA Rule 2165 - Financial Exploitation of Specified Adults",
        """FINRA Rule 2165 permits a member to place a temporary hold on a disbursement of
funds or securities from the account of a specified adult when the member reasonably
believes that financial exploitation has occurred, is occurring, has been attempted, or
will be attempted. A specified adult is a person age 65 or older, or a person age 18 or
older whom the member reasonably believes has a mental or physical impairment that renders
them unable to protect their own interests. The initial temporary hold may last up to 15
business days and may be extended.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_5310_best_execution.md",
        "FINRA Rule 5310 - Best Execution",
        """FINRA Rule 5310 requires that in any transaction for or with a customer, a member
and associated persons use reasonable diligence to ascertain the best market for the
security and buy or sell in that market so the resulting price to the customer is as
favorable as possible under prevailing market conditions. Firms must conduct a regular and
rigorous review of execution quality, at least quarterly.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_4370_business_continuity.md",
        "FINRA Rule 4370 - Business Continuity Plans",
        """FINRA Rule 4370 requires each member to create and maintain a written business
continuity plan (BCP) identifying procedures relating to an emergency or significant
business disruption. The plan must be reasonably designed to enable the member to meet its
existing obligations to customers and address the member's existing relationships with
other broker-dealers and counterparties. Each member must disclose to customers how its
BCP addresses the possibility of a significant business disruption.""",
    ),

    # ---------------- 02_SEC_Regulations ----------------
    (
        "02_SEC_Regulations",
        "sec_reg_bi.md",
        "SEC Regulation Best Interest (Reg BI)",
        """SEC Regulation Best Interest (Reg BI), adopted under the Securities Exchange Act,
establishes a best interest standard of conduct for broker-dealers and associated persons
when making a recommendation of any securities transaction or investment strategy to a
retail customer. Reg BI comprises four component obligations: the Disclosure Obligation,
the Care Obligation, the Conflict of Interest Obligation, and the Compliance Obligation. A
broker-dealer must act in the retail customer's best interest and cannot place its own
financial interests ahead of the customer's interests.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_form_crs.md",
        "SEC Form CRS - Customer/Client Relationship Summary",
        """Form CRS is a relationship summary that broker-dealers and investment advisers
must deliver to retail investors. It is limited to two pages for a standalone broker-dealer
or investment adviser (four pages for a dual registrant) and must be written in plain
English. Form CRS covers the relationships and services the firm offers, fees and costs,
conflicts of interest, the required standard of conduct, and whether the firm and its
financial professionals have reportable legal or disciplinary history.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_rule_17a4.md",
        "SEC Rule 17a-4 - Records Retention",
        """SEC Rule 17a-4 specifies how long broker-dealers must keep various records and in
what format. Many records must be retained for at least three years, the first two years in
an easily accessible place. Certain records must be kept for six years. Records may be
stored on electronic media provided the media preserves the records in a non-rewriteable,
non-erasable format, commonly known as WORM (write once, read many).""",
    ),
    (
        "02_SEC_Regulations",
        "sec_rule_10b5.md",
        "SEC Rule 10b-5 - Employment of Manipulative and Deceptive Devices",
        """SEC Rule 10b-5, adopted under Section 10(b) of the Securities Exchange Act, makes
it unlawful to employ any device, scheme, or artifice to defraud; to make any untrue
statement of a material fact or omit a material fact; or to engage in any act or practice
that operates as a fraud or deceit in connection with the purchase or sale of any security.
Rule 10b-5 is the principal anti-fraud rule used in insider trading enforcement.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_reg_sho.md",
        "SEC Regulation SHO - Short Sales",
        """SEC Regulation SHO governs short selling. It includes a locate requirement, under
which a broker-dealer must have reasonable grounds to believe a security can be borrowed and
delivered before accepting or effecting a short sale order. It also includes close-out
requirements for failures to deliver. Regulation SHO is designed to address abusive naked
short selling and persistent delivery failures.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_reg_s_p.md",
        "SEC Regulation S-P - Privacy of Consumer Financial Information",
        """SEC Regulation S-P requires broker-dealers and investment advisers to adopt
written policies and procedures to protect customer records and information. Under the
safeguards rule, firms must protect against unauthorized access to and use of customer
information. Regulation S-P also governs the delivery of privacy notices and limits the
sharing of nonpublic personal information with nonaffiliated third parties.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_reg_s_id.md",
        "SEC Regulation S-ID - Identity Theft Red Flags",
        """SEC Regulation S-ID, the Identity Theft Red Flags Rule, requires certain financial
institutions and creditors to develop and implement a written identity theft prevention
program designed to detect, prevent, and mitigate identity theft in connection with covered
accounts. The program must include reasonable policies to identify and respond to relevant
red flags and must be periodically updated.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_market_access_rule.md",
        "SEC Rule 15c3-5 - Market Access Rule",
        """SEC Rule 15c3-5, the Market Access Rule, requires broker-dealers with market
access, or that provide customers with market access, to establish risk management controls
and supervisory procedures reasonably designed to manage the financial, regulatory, and
other risks of that access. Controls must prevent the entry of orders that exceed
pre-set credit or capital thresholds and must reject erroneous orders.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_customer_protection_rule.md",
        "SEC Rule 15c3-3 - Customer Protection Rule",
        """SEC Rule 15c3-3, the Customer Protection Rule, requires broker-dealers to maintain
physical possession or control of customers' fully paid and excess margin securities and to
maintain a special reserve bank account for the exclusive benefit of customers. The reserve
computation ensures that customer cash is segregated from the firm's proprietary funds.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_net_capital_rule.md",
        "SEC Rule 15c3-1 - Net Capital Rule",
        """SEC Rule 15c3-1, the Net Capital Rule, requires broker-dealers to maintain minimum
levels of net liquid assets, known as net capital, at all times. The rule is designed to
ensure that a firm can meet its obligations to customers and counterparties and can wind
down in an orderly manner without loss to customers if it fails.""",
    ),

    # ---------------- 03_FIX_Protocol ----------------
    (
        "03_FIX_Protocol",
        "fix_overview.md",
        "FIX Protocol Overview",
        """FIX stands for Financial Information eXchange. It is a messaging standard used for
the electronic communication of securities transactions and pre-trade and post-trade
messages. A FIX message is composed of tag=value pairs separated by a delimiter (the SOH
character, ASCII 0x01). Every message begins with the standard header and ends with a
checksum in tag 10.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_new_order_single.md",
        "FIX NewOrderSingle (MsgType D)",
        """In the FIX protocol, a NewOrderSingle message is identified by MsgType (tag 35)
with a value of D. It is used to submit a single order to a broker or exchange. Key fields
include ClOrdID (tag 11) the client order id, Symbol (tag 55), Side (tag 54) where 1 is Buy
and 2 is Sell, OrderQty (tag 38), and OrdType (tag 40) where 1 is Market and 2 is Limit. A
limit order also carries Price (tag 44).""",
    ),
    (
        "03_FIX_Protocol",
        "fix_execution_report.md",
        "FIX ExecutionReport (MsgType 8)",
        """In the FIX protocol, an ExecutionReport message is identified by MsgType (tag 35)
with a value of 8. It communicates the status of an order. ExecType (tag 150) describes the
reason for the report, and OrdStatus (tag 39) describes the current order state, for example
0 for New, 1 for Partially filled, 2 for Filled, and 4 for Canceled. LastQty (tag 32) and
LastPx (tag 31) report the quantity and price of the most recent fill.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_common_tags.md",
        "Common FIX Tags",
        """Common FIX tags include tag 8 BeginString which identifies the FIX version, tag 9
BodyLength, tag 35 MsgType, tag 49 SenderCompID, tag 56 TargetCompID, tag 34 MsgSeqNum, and
tag 10 CheckSum. The BeginString always appears first and the CheckSum always appears last.
The MsgSeqNum is used to detect gaps and ensure ordered delivery within a FIX session.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_session_management.md",
        "FIX Session Management",
        """A FIX session is established with a Logon message (MsgType A) and terminated with a
Logout message (MsgType 5). Heartbeat messages (MsgType 0) are exchanged at the interval set
by HeartBtInt (tag 108) to keep the session alive. If a participant detects a sequence gap it
sends a ResendRequest (MsgType 2). A TestRequest (MsgType 1) forces the counterparty to send
a Heartbeat.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_order_cancel.md",
        "FIX Order Cancel and Replace",
        """In the FIX protocol, an OrderCancelRequest is MsgType F and is used to cancel a
previously submitted order. An OrderCancelReplaceRequest, MsgType G, modifies an existing
order, for example changing quantity or price. Both reference the original order via OrigClOrdID
(tag 41) and carry a new ClOrdID (tag 11). An OrderCancelReject, MsgType 9, is returned if the
request cannot be honored.""",
    ),

    # ---------------- 04_Compliance_Programs ----------------
    (
        "04_Compliance_Programs",
        "insider_trading_procedures.md",
        "Insider Trading Prevention Procedures",
        """Firms must maintain written policies and procedures to prevent the misuse of
material nonpublic information (MNPI), as required by Section 15(g) of the Securities Exchange
Act. Common controls include information barriers (also called ethical walls) that separate
departments, restricted lists and watch lists of securities, pre-clearance of employee
personal trades, and surveillance of trading around material events. Suspected insider
trading should be escalated to the compliance department and may require filing a suspicious
activity report.""",
    ),
    (
        "04_Compliance_Programs",
        "suspicious_activity_reporting.md",
        "Suspicious Activity Reporting (SAR)",
        """Under the Bank Secrecy Act, broker-dealers must file a Suspicious Activity Report
(SAR) with FinCEN for transactions that are at least 5,000 dollars and that the firm knows,
suspects, or has reason to suspect involve funds from illegal activity, are designed to evade
reporting requirements, have no apparent lawful purpose, or involve use of the firm to
facilitate criminal activity. A SAR generally must be filed within 30 calendar days of
detecting facts that constitute a basis for filing.""",
    ),
    (
        "04_Compliance_Programs",
        "electronic_communications_retention.md",
        "Electronic Communications Recordkeeping",
        """Firms must retain business-related electronic communications, including email,
instant messaging, and text messages, as books and records. Communications must be preserved
in a non-rewriteable, non-erasable (WORM) format consistent with SEC Rule 17a-4, retained for
the applicable period, indexed, and made promptly available to regulators on request. Firms
must also supervise and review electronic communications for compliance.""",
    ),
    (
        "04_Compliance_Programs",
        "customer_complaint_handling.md",
        "Customer Complaint Handling",
        """A customer complaint is any written grievance from a customer or person acting on
behalf of a customer involving the firm or an associated person. Under FINRA Rule 4513 firms
must keep records of written customer complaints and their disposition. Certain complaints must
be reported to FINRA quarterly under Rule 4530. Firms should acknowledge, investigate, and
document the resolution of each complaint.""",
    ),
    (
        "04_Compliance_Programs",
        "gifts_and_entertainment.md",
        "Gifts and Entertainment Policy",
        """Under FINRA Rule 3220, a member or associated person may not give anything of value
in excess of 100 dollars per year to any person where the payment relates to the business of
the recipient's employer. Ordinary business entertainment that is neither so frequent nor so
extensive as to raise a question of propriety is treated separately from gifts. Firms must
keep records of gifts and of business entertainment.""",
    ),
    (
        "04_Compliance_Programs",
        "outside_business_activities.md",
        "Outside Business Activities",
        """Under FINRA Rule 3270, a registered person may not be an employee, independent
contractor, sole proprietor, officer, director, or partner of another business, or be
compensated by another person for any business activity outside the scope of the relationship
with the member firm, unless the person has provided prior written notice to the firm. The
firm must evaluate the activity and may impose conditions or prohibit it.""",
    ),
    (
        "04_Compliance_Programs",
        "private_securities_transactions.md",
        "Private Securities Transactions",
        """Under FINRA Rule 3280, before participating in any private securities transaction,
an associated person must provide written notice to the member firm describing the proposed
transaction and the person's role. If the person will receive selling compensation, the firm
must approve or disapprove the transaction in writing and, if approved, record it on the firm's
books and supervise it as if it were the firm's own.""",
    ),
    (
        "04_Compliance_Programs",
        "reg_bi_care_obligation.md",
        "Reg BI Care Obligation in Practice",
        """The Care Obligation of Regulation Best Interest requires a broker-dealer to exercise
reasonable diligence, care, and skill to understand the potential risks, rewards, and costs of
a recommendation and to have a reasonable basis to believe the recommendation is in the retail
customer's best interest. Cost is an explicit factor that must be considered, though it is not
the only factor. A series of recommended transactions must not be excessive.""",
    ),

    # ---------------- 05_Market_Structure ----------------
    (
        "05_Market_Structure",
        "reg_nms.md",
        "Regulation NMS",
        """Regulation NMS (National Market System) is a set of SEC rules governing US equity
market structure. The Order Protection Rule (Rule 611) requires trading centers to avoid
trade-throughs by not executing at prices inferior to protected quotations displayed by other
trading centers. The Access Rule (Rule 610) addresses access to quotations and caps access
fees. The Sub-Penny Rule (Rule 612) generally prohibits quoting in increments smaller than one
cent for stocks priced at or above one dollar.""",
    ),
    (
        "05_Market_Structure",
        "consolidated_audit_trail.md",
        "Consolidated Audit Trail (CAT)",
        """The Consolidated Audit Trail (CAT), created under SEC Rule 613, is a single
comprehensive database that captures the lifecycle of orders and reportable events in NMS
securities and OTC equity securities across US markets. Broker-dealers must report order,
route, modification, cancellation, and execution events to CAT. CAT is intended to give
regulators the ability to reconstruct market activity and investigate manipulation.""",
    ),
    (
        "05_Market_Structure",
        "market_maker_obligations.md",
        "Market Maker Obligations",
        """A market maker stands ready to buy and sell a security on a continuous basis at
publicly quoted prices and provides liquidity to the market. Registered market makers have
affirmative obligations to maintain continuous two-sided quotations within a specified
percentage of the national best bid and offer. In exchange they may receive certain benefits,
such as an exception from the Regulation SHO locate requirement for bona fide market making.""",
    ),
    (
        "05_Market_Structure",
        "circuit_breakers.md",
        "Market-Wide Circuit Breakers",
        """Market-wide circuit breakers halt trading across US equity markets during severe
declines to reduce volatility and give investors time to assess information. There are three
levels based on the decline in the S&P 500 Index from the prior day's close: Level 1 is a 7
percent decline, Level 2 is a 13 percent decline, and Level 3 is a 20 percent decline. Level 1
and Level 2 halts last 15 minutes if triggered before 3:25 p.m.; a Level 3 halt stops trading
for the remainder of the day.""",
    ),
    (
        "05_Market_Structure",
        "limit_up_limit_down.md",
        "Limit Up-Limit Down (LULD)",
        """The Limit Up-Limit Down (LULD) mechanism prevents trades in individual NMS stocks
from occurring outside specified price bands. The bands are set at a percentage above and below
a reference price based on the average price over the preceding five minutes. If the national
best bid or offer moves to a band and does not move back within 15 seconds, a trading pause of
five minutes is triggered.""",
    ),
    (
        "05_Market_Structure",
        "dark_pools.md",
        "Dark Pools and ATSs",
        """A dark pool is a type of alternative trading system (ATS) that does not display
quotations publicly before execution. ATSs are registered as broker-dealers and are regulated
under Regulation ATS. Dark pools let institutional investors trade large blocks with reduced
market impact, but they must provide fair access and comply with transparency and reporting
requirements, including Form ATS-N for NMS stock ATSs.""",
    ),
    (
        "05_Market_Structure",
        "short_sale_circuit_breaker.md",
        "Short Sale Circuit Breaker (Rule 201)",
        """Regulation SHO Rule 201, the alternative uptick rule, is a short sale price test
triggered when a covered security's price declines by 10 percent or more from the prior day's
closing price. Once triggered, short sales may only be executed at a price above the current
national best bid for the remainder of the day and the following day.""",
    ),

    # ---------------- 06_Registration_Licensing ----------------
    (
        "06_Registration_Licensing",
        "series_7.md",
        "Series 7 - General Securities Representative",
        """The Series 7 exam, the General Securities Representative Qualification Examination,
licenses a representative to sell a broad range of securities products. Since the exam was
restructured, candidates must first pass the Securities Industry Essentials (SIE) exam, and the
Series 7 serves as the top-off qualification. The Series 7 covers equity and debt instruments,
options, investment company products, and the rules governing their sale.""",
    ),
    (
        "06_Registration_Licensing",
        "series_63_66.md",
        "Series 63 and Series 66",
        """The Series 63, the Uniform Securities Agent State Law Examination, qualifies an
individual to transact securities business within a state and is based on the Uniform
Securities Act. The Series 66 combines the Series 63 and the Series 65 (investment adviser
representative) content into a single exam and is typically taken with the Series 7.""",
    ),
    (
        "06_Registration_Licensing",
        "sie_exam.md",
        "Securities Industry Essentials (SIE)",
        """The Securities Industry Essentials (SIE) exam is an introductory-level exam that
assesses basic securities industry knowledge, including concepts such as types of products and
their risks, the structure of the markets, regulatory agencies and their functions, and
prohibited practices. The SIE can be taken by anyone age 18 or older and does not require
association with a firm.""",
    ),
    (
        "06_Registration_Licensing",
        "form_u4_u5.md",
        "Form U4 and Form U5",
        """Form U4 is the Uniform Application for Securities Industry Registration used to
register associated persons with FINRA, states, and self-regulatory organizations. It captures
disclosure information including criminal, regulatory, and financial events. Form U5 is the
Uniform Termination Notice filed when a registered person leaves a firm; it must be filed within
30 days of termination and must state the reason for termination.""",
    ),
    (
        "06_Registration_Licensing",
        "continuing_education.md",
        "Continuing Education Requirements",
        """FINRA's continuing education program has two components. The Regulatory Element
requires registered persons to complete training on regulatory topics annually by December 31.
The Firm Element requires member firms to deliver an annual training plan to covered registered
persons that addresses securities products, services, and strategies the firm offers and the
applicable regulatory requirements.""",
    ),

    # ---------------- 07_Risk_And_Reporting ----------------
    (
        "07_Risk_And_Reporting",
        "trace_reporting.md",
        "TRACE Reporting",
        """TRACE, the Trade Reporting and Compliance Engine, is the FINRA facility for mandatory
reporting of over-the-counter transactions in eligible fixed income securities. Firms must
report TRACE-eligible secondary market transactions generally within 15 minutes of the time of
execution. TRACE increases post-trade transparency in the corporate and agency bond markets.""",
    ),
    (
        "07_Risk_And_Reporting",
        "large_trader_reporting.md",
        "Large Trader Reporting (Rule 13h-1)",
        """SEC Rule 13h-1 requires persons whose transactions in NMS securities equal or exceed
two million shares or 20 million dollars in a day, or 20 million shares or 200 million dollars in
a month, to identify themselves as large traders by filing Form 13H with the SEC. Registered
broker-dealers must maintain transaction records for large traders and report them on request.""",
    ),
    (
        "07_Risk_And_Reporting",
        "margin_requirements.md",
        "Margin Requirements (Regulation T)",
        """Regulation T, administered by the Federal Reserve Board, governs the extension of
credit by broker-dealers for the purchase of securities. The initial margin requirement under
Regulation T is generally 50 percent of the purchase price of marginable securities. FINRA Rule
4210 sets maintenance margin requirements, generally 25 percent of the current market value of
securities in a margin account.""",
    ),
    (
        "07_Risk_And_Reporting",
        "pattern_day_trader.md",
        "Pattern Day Trader Rule",
        """A pattern day trader is a customer who executes four or more day trades within five
business days in a margin account, where the day trades represent more than six percent of total
trades in that period. A pattern day trader must maintain minimum equity of 25,000 dollars in the
margin account on any day that day trading occurs, and may not day trade without meeting this
minimum.""",
    ),
    (
        "07_Risk_And_Reporting",
        "regulation_t_payment.md",
        "Settlement and Payment (T+1)",
        """US securities transactions in equities and corporate bonds settle on a T+1 basis,
meaning settlement occurs one business day after the trade date. The move to T+1 shortened the
prior T+2 cycle to reduce counterparty and market risk. Under Regulation T, customers must
generally pay for securities purchases promptly and no later than the applicable settlement
framework allows.""",
    ),
    (
        "07_Risk_And_Reporting",
        "liquidity_risk_management.md",
        "Liquidity Risk Management",
        """Broker-dealers are expected to maintain liquidity risk management practices that
include stress testing, maintaining a liquidity reserve of highly liquid assets, and
contingency funding plans. These expectations complement the Net Capital Rule and are designed
to ensure a firm can withstand a stressed funding environment without harming customers.""",
    ),
    (
        "07_Risk_And_Reporting",
        "cybersecurity_obligations.md",
        "Cybersecurity Obligations",
        """Firms must address cybersecurity risk as part of their obligations to protect customer
records and information under Regulation S-P and to maintain reasonable supervisory systems.
Expected practices include governance and risk assessment, access controls, data encryption,
vendor management, incident response planning, and staff training. A cybersecurity incident
affecting customer information may trigger notification obligations.""",
    ),
]


def write_corpus() -> int:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for category, filename, title, body in DOCUMENTS:
        cat_dir = CORPUS_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        # Normalize body whitespace (wrapped source -> clean paragraph text).
        clean = " ".join(body.split())
        text = f"# {title}\n\n{clean}\n"
        (cat_dir / filename).write_text(text, encoding="utf-8")
        count += 1
    return count


if __name__ == "__main__":
    n = write_corpus()
    print(f"Wrote {n} documents to {CORPUS_DIR}")
