#!/usr/bin/env python3
"""
Generate a ~100-document compliance/markets knowledge base for benchmarking.

The content is deterministic, self-contained, and requires no network access or external
LLM API keys, so it runs cleanly on a local/Linux/GPU machine. The golden answers in
``data/eval_questions.json`` are grounded in the exact text produced here. Running this
script writes Markdown files under ``data/corpus/`` (organized by category). It does not
touch any database; feed the output to the normal ingestion pipeline:

    python data/generate_dataset.py
    python -m ingestion.ingest --documents ./data/corpus

Re-running overwrites the corpus deterministically. The corpus spans nine categories
(FINRA rules, SEC regulations, FIX protocol, compliance programs, market structure,
registration/licensing, risk/reporting, clearing/settlement, and ethics/conduct). The
first 53 documents are unchanged so that evaluation questions q1-q20 remain grounded; the
remainder expand coverage for a larger comparative benchmark.
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

    # ================================================================
    # Documents added to expand the corpus to ~100 for the benchmark.
    # Everything above this line is unchanged so q1-q20 stay grounded.
    # ================================================================

    # ---------------- 01_FINRA_Rules (additions) ----------------
    (
        "01_FINRA_Rules",
        "finra_2210_communications.md",
        "FINRA Rule 2210 - Communications with the Public",
        """FINRA Rule 2210 governs member communications with the public and sorts them into
three categories: retail communication, correspondence, and institutional communication. A
retail communication is distributed to more than 25 retail investors within any 30 calendar-day
period. Communications must be fair and balanced, may not be misleading, and must be approved by
a registered principal before use where required. Certain retail communications must be filed
with FINRA's Advertising Regulation Department.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_2267_bcp_disclosure.md",
        "FINRA Rule 2267 - Investor Education and Protection",
        """FINRA Rule 2267 requires members to provide customers, once each calendar year, with
the FINRA BrokerCheck hotline number, the FINRA website address, and a statement regarding the
availability of an investor brochure that describes BrokerCheck. This helps customers verify the
background and disciplinary history of firms and associated persons.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_3240_borrowing.md",
        "FINRA Rule 3240 - Borrowing From or Lending to Customers",
        """FINRA Rule 3240 generally prohibits a registered person from borrowing money from or
lending money to a customer unless the firm has written procedures permitting it and the
arrangement meets a permitted condition, such as a family relationship or a lending relationship
with a financial institution in the business of lending. The arrangement must usually be
pre-approved in writing by the firm.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_4210_margin.md",
        "FINRA Rule 4210 - Margin Requirements",
        """FINRA Rule 4210 sets maintenance margin requirements for securities carried in a
customer margin account. The general maintenance requirement is 25 percent of the current market
value of long securities. The rule also addresses day-trading margin, pattern day traders, and
special maintenance requirements for concentrated or volatile positions.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_4530_reporting.md",
        "FINRA Rule 4530 - Reporting Requirements",
        """FINRA Rule 4530 requires members to report specified events to FINRA, such as findings
that the firm or an associated person violated securities laws, certain written customer
complaints, and specified disciplinary actions. Many events must be reported within 30 calendar
days after the member knows or should have known of their existence, and statistical complaint
information is reported quarterly.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_2360_options.md",
        "FINRA Rule 2360 - Options",
        """FINRA Rule 2360 governs options trading by members, including account approval, position
and exercise limits, and the delivery of the options disclosure document (ODD) to customers at or
before approval of an options account. Firms must have reasonable grounds to believe options
trading is appropriate for the customer based on the customer's investment objectives and
experience.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_2124_net_transactions.md",
        "FINRA Rule 2124 - Net Transactions with Customers",
        """FINRA Rule 2124 permits a member to execute net transactions with a customer only with
the customer's consent. A net transaction is a principal trade in which the member, after having
received an order, buys or sells the security and reports to the customer a price that is net of
the member's mark-up or mark-down. Firms must obtain the required consent and keep records of it.""",
    ),
    (
        "01_FINRA_Rules",
        "finra_3260_discretionary.md",
        "FINRA Rule 3260 - Discretionary Accounts",
        """FINRA Rule 3260 prohibits a member or registered person from exercising discretionary
power in a customer's account unless the customer has given prior written authorization and the
account has been accepted in writing by the firm. Each discretionary order must be identified as
such, and discretionary accounts must be reviewed at frequent intervals.""",
    ),

    # ---------------- 02_SEC_Regulations (additions) ----------------
    (
        "02_SEC_Regulations",
        "sec_reg_atdirect.md",
        "SEC Regulation ATS - Alternative Trading Systems",
        """SEC Regulation ATS establishes the framework under which an alternative trading system
may operate as a registered broker-dealer rather than a national securities exchange. An ATS must
file Form ATS, meet fair access requirements when its volume in a security crosses specified
thresholds, and comply with recordkeeping and systems requirements. NMS stock ATSs must also file
Form ATS-N disclosing operations and conflicts.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_rule_606_order_routing.md",
        "SEC Rule 606 - Order Routing Disclosure",
        """SEC Rule 606 requires broker-dealers to publish quarterly reports on their routing of
non-directed customer orders in NMS securities, including the venues to which orders were routed
and any payment for order flow arrangements. On customer request, firms must also disclose the
specific routing of that customer's orders for the prior six months.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_rule_605_execution_quality.md",
        "SEC Rule 605 - Execution Quality Statistics",
        """SEC Rule 605 requires market centers that trade NMS securities to make monthly,
standardized, publicly available reports on execution quality. The reports include statistics such
as effective spreads, realized spreads, speed of execution, and price improvement, enabling
comparison of execution quality across venues.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_reg_fd.md",
        "SEC Regulation FD - Fair Disclosure",
        """SEC Regulation FD (Fair Disclosure) prohibits selective disclosure of material nonpublic
information by issuers to analysts or investors. When an issuer discloses such information, it must
do so broadly and publicly, simultaneously for intentional disclosures or promptly for unintentional
ones, so that all investors have equal access to the information.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_rule_144.md",
        "SEC Rule 144 - Resale of Restricted Securities",
        """SEC Rule 144 provides a safe harbor for the public resale of restricted and control
securities. Conditions include a holding period of at least six months for securities of a reporting
company (one year for a non-reporting company), the availability of current public information,
volume limitations for affiliates, and, for affiliates, the filing of Form 144 when sales exceed
specified thresholds.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_reg_d.md",
        "SEC Regulation D - Private Placements",
        """SEC Regulation D provides exemptions from registration for certain private offerings of
securities. Rule 506(b) permits raising an unlimited amount from accredited investors and up to 35
non-accredited but sophisticated investors without general solicitation. Rule 506(c) permits general
solicitation provided all purchasers are accredited investors and the issuer takes reasonable steps
to verify accredited status.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_reg_m.md",
        "SEC Regulation M - Anti-Manipulation",
        """SEC Regulation M is designed to prevent manipulation by participants in a securities
offering. It restricts the ability of underwriters, issuers, and other distribution participants to
bid for or purchase the offered security during a restricted period. Rule 101 and Rule 102 govern
activities by distribution participants and issuers, and Rule 104 addresses permissible stabilizing
bids.""",
    ),
    (
        "02_SEC_Regulations",
        "sec_whistleblower.md",
        "SEC Whistleblower Program",
        """The SEC whistleblower program, established under the Dodd-Frank Act, pays monetary awards
to eligible individuals who voluntarily provide original information that leads to a successful
enforcement action with sanctions over 1,000,000 dollars. Awards range from 10 percent to 30 percent
of the monetary sanctions collected. The program also protects whistleblowers from retaliation by
their employers.""",
    ),

    # ---------------- 03_FIX_Protocol (additions) ----------------
    (
        "03_FIX_Protocol",
        "fix_order_types.md",
        "FIX Order Types (OrdType tag 40)",
        """In the FIX protocol, the OrdType field (tag 40) specifies the order type. Common values
are 1 for Market, 2 for Limit, 3 for Stop, and 4 for Stop Limit. A Limit order requires a Price (tag
44). A Stop order requires a StopPx (tag 99). The TimeInForce field (tag 59) qualifies how long the
order remains active, for example 0 for Day and 1 for Good Till Cancel.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_market_data.md",
        "FIX Market Data Messages",
        """In the FIX protocol, a MarketDataRequest is MsgType V and subscribes to quotes or trades.
The venue responds with a MarketDataSnapshotFullRefresh (MsgType W) containing the full book snapshot
or a MarketDataIncrementalRefresh (MsgType X) containing updates. MDEntryType (tag 269) distinguishes
entry kinds, for example 0 for Bid, 1 for Offer, and 2 for Trade.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_reject_messages.md",
        "FIX Reject and Business Reject",
        """In the FIX protocol, a session-level Reject (MsgType 3) indicates a message could not be
processed due to a session-level rule violation, such as an invalid tag. A BusinessMessageReject
(MsgType j) indicates an application-level rejection, carrying RefMsgType (tag 372) and a
BusinessRejectReason (tag 380) that explains why the message was rejected.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_versions.md",
        "FIX Protocol Versions",
        """The FIX protocol has evolved through several versions. FIX 4.2 and FIX 4.4 remain widely
deployed for order routing. FIX 5.0 introduced the FIXT transport layer, which separates the session
layer from the application layer so that the application version can evolve independently. The
BeginString (tag 8) identifies the session protocol version, such as FIX.4.4 or FIXT.1.1.""",
    ),
    (
        "03_FIX_Protocol",
        "fix_checksum.md",
        "FIX Checksum Calculation (tag 10)",
        """In the FIX protocol, the CheckSum field (tag 10) is always the final field of a message. It
is computed by summing the ASCII values of all bytes in the message up to but not including the
checksum field, taking the result modulo 256, and formatting it as a three-digit value. The checksum
lets the receiver detect transmission corruption.""",
    ),

    # ---------------- 04_Compliance_Programs (additions) ----------------
    (
        "04_Compliance_Programs",
        "best_interest_disclosure.md",
        "Reg BI Disclosure Obligation in Practice",
        """The Disclosure Obligation of Regulation Best Interest requires a broker-dealer to provide
retail customers, in writing and before or at the time of a recommendation, full and fair disclosure
of material facts about the scope and terms of the relationship, including the capacity in which the
firm is acting, material fees and costs, and the type and scope of services, as well as material
limitations on the securities or investment strategies that may be recommended.""",
    ),
    (
        "04_Compliance_Programs",
        "conflict_of_interest_obligation.md",
        "Reg BI Conflict of Interest Obligation",
        """The Conflict of Interest Obligation of Regulation Best Interest requires a broker-dealer to
establish, maintain, and enforce written policies and procedures reasonably designed to identify and
at a minimum disclose, or eliminate, conflicts of interest. Firms must mitigate conflicts that create
an incentive for associated persons to place their interest ahead of the retail customer's interest,
and must eliminate sales contests and quotas based on specific securities within a limited period.""",
    ),
    (
        "04_Compliance_Programs",
        "aml_customer_identification.md",
        "AML Customer Identification Program (CIP)",
        """Under the Bank Secrecy Act and its implementing rules, broker-dealers must maintain a written
Customer Identification Program (CIP) as part of their AML program. The CIP must collect, at a minimum,
the customer's name, date of birth, address, and an identification number, and must include
risk-based procedures to verify identity and to check customers against government lists. Records of
the information used to verify identity must be retained.""",
    ),
    (
        "04_Compliance_Programs",
        "aml_cdd_beneficial_ownership.md",
        "AML Customer Due Diligence and Beneficial Ownership",
        """The Customer Due Diligence (CDD) rule requires covered financial institutions to identify and
verify the beneficial owners of legal entity customers. A beneficial owner includes each individual who
owns 25 percent or more of the equity interests of the entity and a single individual with significant
responsibility to control or manage the entity. Firms must also understand the nature and purpose of
customer relationships and conduct ongoing monitoring.""",
    ),
    (
        "04_Compliance_Programs",
        "books_records_requirements.md",
        "Books and Records Requirements",
        """Broker-dealers must make and keep current detailed books and records under SEC Rules 17a-3 and
17a-4 and FINRA Rule 4511. Required records include blotters, ledgers, order tickets, trade
confirmations, account records, and communications. Rule 17a-3 specifies what records must be created,
and Rule 17a-4 specifies how long they must be retained and in what format.""",
    ),
    (
        "04_Compliance_Programs",
        "trade_confirmations.md",
        "Trade Confirmations (SEC Rule 10b-10)",
        """SEC Rule 10b-10 requires broker-dealers to give or send a written confirmation to a customer at
or before completion of a securities transaction. The confirmation must disclose key terms such as the
date and time of the transaction, the identity and quantity of the security, the price, whether the firm
acted as agent or principal, and the commission or mark-up where required.""",
    ),
    (
        "04_Compliance_Programs",
        "regulation_bi_compliance_obligation.md",
        "Reg BI Compliance Obligation",
        """The Compliance Obligation of Regulation Best Interest requires a broker-dealer to establish,
maintain, and enforce written policies and procedures reasonably designed to achieve compliance with
Regulation Best Interest as a whole. This is distinct from the policies required specifically for
conflicts of interest and focuses on the firm's overall system for complying with the rule.""",
    ),

    # ---------------- 05_Market_Structure (additions) ----------------
    (
        "05_Market_Structure",
        "nbbo.md",
        "National Best Bid and Offer (NBBO)",
        """The National Best Bid and Offer (NBBO) is the highest available bid price and the lowest
available offer price for an NMS security across all exchanges and reporting market centers. The NBBO is
disseminated through the consolidated quotation system and serves as a key reference point for best
execution analysis and for the Order Protection Rule under Regulation NMS.""",
    ),
    (
        "05_Market_Structure",
        "payment_for_order_flow.md",
        "Payment for Order Flow",
        """Payment for order flow is compensation a broker-dealer receives for routing customer orders to a
particular market maker or venue for execution. The practice is legal but creates a conflict of interest
and must be disclosed, including in SEC Rule 606 order-routing reports and in new-account and annual
disclosures. Firms must still satisfy their best execution obligations regardless of such payments.""",
    ),
    (
        "05_Market_Structure",
        "odd_lots.md",
        "Round Lots, Odd Lots, and Mixed Lots",
        """In US equity markets a round lot is traditionally 100 shares. An odd lot is a quantity smaller
than a round lot, and a mixed lot is a quantity larger than a round lot that is not a whole multiple of
one. Historically odd-lot orders were not reflected in the public quotation, though odd-lot trades are
reported to the consolidated tape and odd-lot data has been incorporated into market data feeds.""",
    ),
    (
        "05_Market_Structure",
        "tick_size.md",
        "Tick Size and the Sub-Penny Rule",
        """Tick size is the minimum price increment at which a security may be quoted or traded. Under
Regulation NMS Rule 612, the Sub-Penny Rule, market participants generally may not display, rank, or
accept quotations in NMS stocks priced at one dollar or more in an increment smaller than one cent.
Stocks priced below one dollar may be quoted in smaller increments.""",
    ),
    (
        "05_Market_Structure",
        "market_on_close.md",
        "Market-on-Close and Closing Auctions",
        """A market-on-close (MOC) order is an order to buy or sell at the official closing price,
executed in the primary exchange's closing auction. Closing auctions aggregate buy and sell interest to
establish a single closing price and are a major source of end-of-day liquidity. Exchanges set cut-off
times after which MOC orders generally may not be entered or canceled.""",
    ),
    (
        "05_Market_Structure",
        "trade_reporting_facility.md",
        "Trade Reporting Facilities (TRFs)",
        """Trades executed away from an exchange, such as those in dark pools or internalized by a
broker-dealer, are reported to a FINRA Trade Reporting Facility (TRF). The TRF disseminates these
over-the-counter trades to the consolidated tape. Firms generally must report such trades as soon as
practicable and within the time limits specified by FINRA rules, typically within 10 seconds of
execution for most transactions.""",
    ),

    # ---------------- 06_Registration_Licensing (additions) ----------------
    (
        "06_Registration_Licensing",
        "series_24.md",
        "Series 24 - General Securities Principal",
        """The Series 24 exam, the General Securities Principal Qualification Examination, qualifies an
individual to supervise and manage branch activities such as trading, underwriting, and the conduct of
registered representatives. A Series 24 principal is responsible for approving communications,
supervising sales practices, and overseeing compliance with applicable rules.""",
    ),
    (
        "06_Registration_Licensing",
        "series_79.md",
        "Series 79 - Investment Banking Representative",
        """The Series 79 exam qualifies an individual to perform investment banking activities, including
advising on or facilitating debt and equity offerings and mergers and acquisitions. Like other
representative-level exams, it requires first passing the Securities Industry Essentials (SIE) exam, with
the Series 79 serving as the specialized top-off qualification.""",
    ),
    (
        "06_Registration_Licensing",
        "series_99.md",
        "Series 99 - Operations Professional",
        """The Series 99 exam, the Operations Professional Qualification Examination, is required for
certain covered operations personnel at member firms whose functions include activities such as account
transfers, settlement, and recordkeeping. It is intended to ensure that operations professionals
understand the regulatory framework relevant to their back-office responsibilities.""",
    ),
    (
        "06_Registration_Licensing",
        "series_65.md",
        "Series 65 - Investment Adviser Representative",
        """The Series 65 exam, the Uniform Investment Adviser Law Examination, qualifies an individual to
act as an investment adviser representative. It covers topics including economics, investment vehicles,
client recommendations, and the legal and regulatory framework for investment advisers, including
fiduciary duty under the Investment Advisers Act and state law.""",
    ),
    (
        "06_Registration_Licensing",
        "statutory_disqualification.md",
        "Statutory Disqualification",
        """A person is subject to statutory disqualification from association with a member firm if they
have been expelled or barred by a self-regulatory organization, have had a securities registration
revoked, have been convicted of certain crimes within the prior ten years, or have made certain false
statements to regulators. A firm seeking to employ such a person generally must file an application
through FINRA's eligibility process.""",
    ),

    # ---------------- 07_Risk_And_Reporting (additions) ----------------
    (
        "07_Risk_And_Reporting",
        "reg_t_free_riding.md",
        "Free-Riding and Settlement",
        """Free-riding occurs when a customer buys a security in a cash account and sells it before paying
for the purchase with settled funds. Regulation T prohibits free-riding, and a cash account that engages
in it may be subject to a 90-day restriction requiring the customer to have sufficient settled funds in
the account before purchases are executed.""",
    ),
    (
        "07_Risk_And_Reporting",
        "sipc_protection.md",
        "SIPC Protection",
        """The Securities Investor Protection Corporation (SIPC) protects customers of a failed broker-dealer
by returning cash and securities, up to 500,000 dollars per customer, of which up to 250,000 dollars may
be for cash claims. SIPC protection covers the custody risk of a broker-dealer failure; it does not
protect against a decline in the market value of investments.""",
    ),
    (
        "07_Risk_And_Reporting",
        "form_bd.md",
        "Form BD - Broker-Dealer Registration",
        """Form BD is the Uniform Application for Broker-Dealer Registration filed with the SEC through the
Central Registration Depository to register as a broker-dealer. It captures information about the firm's
ownership, control persons, business activities, and any disciplinary history. Material changes must be
kept current through amendments.""",
    ),
    (
        "07_Risk_And_Reporting",
        "focus_report.md",
        "FOCUS Report",
        """The FOCUS Report (Financial and Operational Combined Uniform Single report) is a periodic report
that broker-dealers must file with their regulators containing financial and operational data, including
the net capital computation. Most firms file FOCUS reports monthly or quarterly depending on their size
and activities, allowing regulators to monitor financial condition.""",
    ),
    (
        "07_Risk_And_Reporting",
        "regulation_sci.md",
        "Regulation SCI",
        """SEC Regulation SCI (Systems Compliance and Integrity) applies to certain key market participants
such as exchanges, clearing agencies, and large ATSs. It requires them to have policies and procedures to
ensure their technology systems have adequate capacity, integrity, resiliency, and security, to take
corrective action on systems issues, and to notify the SEC of significant systems events.""",
    ),
    (
        "07_Risk_And_Reporting",
        "stress_testing.md",
        "Stress Testing and Capital Adequacy",
        """Stress testing evaluates how a firm's capital and liquidity would withstand severe but plausible
adverse scenarios, such as sharp market declines, funding shortfalls, or counterparty defaults. For
broker-dealers, stress testing complements the Net Capital Rule and liquidity risk management by helping
firms identify vulnerabilities before they threaten customers or counterparties.""",
    ),
    (
        "07_Risk_And_Reporting",
        "position_limits.md",
        "Position and Exercise Limits",
        """Position limits cap the number of option contracts on the same side of the market that a single
investor or group acting in concert may hold in a given underlying security. Exercise limits cap how many
contracts may be exercised within a set number of business days. These limits are designed to prevent any
single participant from exerting undue influence or manipulating the underlying market.""",
    ),

    # ---------------- 08_Clearing_Settlement (new category) ----------------
    (
        "08_Clearing_Settlement",
        "dtcc_overview.md",
        "DTCC and Central Clearing",
        """The Depository Trust and Clearing Corporation (DTCC) provides clearing, settlement, and custody
services for US securities markets through subsidiaries. Its subsidiary the Depository Trust Company (DTC)
acts as the central securities depository holding securities in book-entry form, while the National
Securities Clearing Corporation (NSCC) clears and settles broker-to-broker equity trades.""",
    ),
    (
        "08_Clearing_Settlement",
        "nscc_cns.md",
        "NSCC and Continuous Net Settlement",
        """The National Securities Clearing Corporation (NSCC) uses Continuous Net Settlement (CNS) to net
each member's obligations in a security down to a single net long or short position per settlement day.
NSCC acts as the central counterparty, becoming the buyer to every seller and the seller to every buyer,
which reduces counterparty risk and the number of deliveries required.""",
    ),
    (
        "08_Clearing_Settlement",
        "novation.md",
        "Novation and the Central Counterparty",
        """Novation is the legal process by which a central counterparty (CCP) interposes itself between the
two original trade counterparties, replacing the single contract between them with two contracts, one
between each party and the CCP. After novation, each party faces the CCP rather than the original
counterparty, which concentrates and manages counterparty credit risk.""",
    ),
    (
        "08_Clearing_Settlement",
        "settlement_fails.md",
        "Settlement Fails and Buy-Ins",
        """A settlement fail occurs when a party does not deliver securities or pay for them by the
settlement date. Persistent fails may be addressed through a buy-in, in which the receiving party
purchases the undelivered securities in the market and charges any additional cost to the failing party.
Regulation SHO imposes close-out requirements for certain fails to deliver.""",
    ),
    (
        "08_Clearing_Settlement",
        "margin_at_ccp.md",
        "Initial and Variation Margin at a CCP",
        """A central counterparty collects two main types of margin from its clearing members. Initial margin
is collateral posted to cover potential future exposure over the time it would take to close out a
defaulting member's positions. Variation margin is collected or paid daily to settle the change in market
value of open positions, preventing losses from accumulating.""",
    ),
    (
        "08_Clearing_Settlement",
        "default_waterfall.md",
        "CCP Default Waterfall",
        """A central counterparty manages a member default through a default waterfall, the ordered sequence
of financial resources used to cover losses. The typical order is the defaulting member's initial margin
and default fund contribution first, then the CCP's own contribution (skin in the game), then the
mutualized default fund contributions of non-defaulting members, and finally any assessment powers.""",
    ),

    # ---------------- 09_Ethics_Conduct (new category) ----------------
    (
        "09_Ethics_Conduct",
        "fiduciary_duty.md",
        "Fiduciary Duty of Investment Advisers",
        """Under the Investment Advisers Act, an investment adviser owes a fiduciary duty to its clients,
comprising a duty of care and a duty of loyalty. The duty of care requires providing advice in the
client's best interest, seeking best execution, and providing ongoing advice and monitoring as agreed.
The duty of loyalty requires the adviser not to place its own interests ahead of the client's and to
fully and fairly disclose material conflicts of interest.""",
    ),
    (
        "09_Ethics_Conduct",
        "churning.md",
        "Churning",
        """Churning is excessive trading in a customer's account by a broker who has control over the account,
carried out primarily to generate commissions rather than to benefit the customer. It violates
anti-fraud provisions and the quantitative suitability obligation. Indicators include a high turnover
rate and a high cost-to-equity ratio relative to the customer's objectives.""",
    ),
    (
        "09_Ethics_Conduct",
        "front_running.md",
        "Front-Running",
        """Front-running is the prohibited practice of trading a security or related option for one's own
account while taking advantage of advance knowledge of a pending customer or block order that is likely to
move the market. It breaches the duty owed to the customer and market and is addressed by FINRA rules
prohibiting trading ahead of customer orders and block transactions.""",
    ),
    (
        "09_Ethics_Conduct",
        "market_manipulation.md",
        "Market Manipulation",
        """Market manipulation includes schemes intended to deceive investors by artificially affecting the
price or volume of a security. Examples include spoofing, which is placing orders with the intent to
cancel before execution to create a false impression of demand, layering, wash trades between accounts
under common control, and pump-and-dump schemes. Such conduct violates anti-fraud provisions of the
securities laws.""",
    ),
    (
        "09_Ethics_Conduct",
        "selling_away.md",
        "Selling Away",
        """Selling away is the prohibited practice in which a registered person participates in a securities
transaction outside the regular course or scope of their association with the firm without providing the
required prior written notice and, where applicable, obtaining firm approval. It is addressed by the
private securities transaction rule and undermines the firm's supervision of the person's activities.""",
    ),
    (
        "09_Ethics_Conduct",
        "code_of_ethics.md",
        "Code of Ethics (Advisers Act Rule 204A-1)",
        """Under Rule 204A-1 of the Investment Advisers Act, a registered investment adviser must adopt a
written code of ethics that sets standards of business conduct, requires compliance with federal
securities laws, and requires access persons to report their personal securities holdings and
transactions periodically. The code must also require access persons to obtain pre-approval for certain
investments, such as initial public offerings and private placements.""",
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
