# Verified research: Superteam Earn World Cup hackathon powered by TxODDS / TxLINE

## Facts
- [high] Submission window is June 24, 2026 15:00 UTC to July 19, 2026 23:59 UTC. _(source: txodds-world-cup-brief.md)_
- [high] Winner announcement on July 29, 2026 15:00 UTC. _(source: txodds-world-cup-brief.md)_
- [high] Team size maximum 3. _(source: txodds-world-cup-brief.md)_
- [high] Required submission: working build, demo video up to 5 min, public repo, deployed website or functional API/devnet endpoint, brief technical documentation, TxLINE endpoint list, and API feedback. _(source: txodds-world-cup-brief.md)_
- [high] TxLINE provides high-performance data layer for real-time sports data and consensus betting odds. _(source: txodds-world-cup-brief.md)_
- [high] TxLINE covers all 104 World Cup matches with normalized JSON schema. _(source: txodds-world-cup-brief.md)_
- [high] TxLINE updates are cryptographically signed and anchored on Solana. _(source: txodds-world-cup-brief.md)_
- [high] Hackathon builders receive free TxLINE access until the submission deadline. _(source: txodds-world-cup-brief.md)_
- [high] Common requirements: TxLINE data must be a primary live input; products must be functional, not wireframes or pitch decks; demo video quality matters because live matches may not be active during judging. _(source: txodds-world-cup-brief.md)_
- [high] Participants must comply with gambling, gaming, financial, consumer protection, and securities laws. _(source: txodds-world-cup-brief.md)_
- [high] Track 1 (Prediction Markets and Settlement) prize pool: 18,000 USDT (1st 12k, 2nd 4k, 3rd 2k). _(source: txodds-world-cup-brief.md)_
- [medium] Track 1 observed submissions: 112. _(source: txodds-world-cup-brief.md)_
- [high] Track 1 focuses on prediction platforms, sportsbook interfaces, data dashboards, decentralized prediction markets, AMMs, escrow settlement engines, parametric sports insurance, prop bets. _(source: txodds-world-cup-brief.md)_
- [high] Track 1 judges value smooth TxLINE ingestion, compelling soccer/analytical UX, clean deterministic resolution/validation code, optional Merkle proof verification, custom Solana settlement logic using TxLINE validation primitives. _(source: txodds-world-cup-brief.md)_
- [high] Track 1 constraint: TxLINE credit token cannot be used for user wagering or transfers; user funds can be held in other assets like USDC. _(source: txodds-world-cup-brief.md)_
- [high] Track 1 encourages using TxLINE Merkle proofs and CPI into TxLINE validate_stat for trustless settlement. _(source: txodds-world-cup-brief.md)_
- [high] Track 2 (Consumer and Fan Experiences) prize pool: 16,000 USDT (1st 10k, 2nd 4k, 3rd 2k). _(source: txodds-world-cup-brief.md)_
- [medium] Track 2 observed submissions: 113. _(source: txodds-world-cup-brief.md)_
- [high] Track 2 focuses on mainstream fan products using live scores, odds, match events; example ideas: group sweepstakes, AI pundit bots, hi-lo stats games. _(source: txodds-world-cup-brief.md)_
- [high] Track 2 judges value fan accessibility and polish, real-time responsiveness, original consumer interaction models, monetization path, complete end-to-end execution. _(source: txodds-world-cup-brief.md)_
- [high] Track 2 extra requirement: sign up through Solana. _(source: txodds-world-cup-brief.md)_
- [high] Track 3 (Trading Tools and Agents) prize pool: 16,000 USDT (1st 10k, 2nd 4k, 3rd 2k). _(source: txodds-world-cup-brief.md)_
- [medium] Track 3 observed submissions: 91. _(source: txodds-world-cup-brief.md)_
- [high] Track 3 focuses on autonomous agents ingesting TxLINE feeds and executing defined strategies; example ideas: sharp movement detector, agent-vs-agent arena, in-play market maker. _(source: txodds-world-cup-brief.md)_
- [high] Track 3 judges value core feed ingestion, autonomous operation, deterministic and mathematically defensible strategy logic, novelty, production readiness for trading teams. _(source: txodds-world-cup-brief.md)_

## Inference
- Winning products must deeply integrate TxLINE live data, as it is the central dependency and judging criterion. — TxLINE is specified as primary live input for all tracks, and judges explicitly value smooth ingestion.
- High-quality demo videos with simulated real-time data are critical because live matches may not be active during judging. — Common requirements stress demo video quality for that reason.
- Projects with simple, well-scoped builds have an advantage given the short hackathon window (just under 4 weeks). — Submission deadline is tight; extensive feature sets risk incomplete demos.
- Track 1 carries higher legal/regulatory risk due to direct betting mechanics; judges will favor compliant designs or clearly separated non-wagerable demos. — Explicit legal warnings and prohibition on TxLINE token wagering suggest compliance scrutiny.
- Track 3 may have lower submission volume (91 observed) offering less direct competition, but requires strong algorithmic novelty. — Emphasis on mathematically defensible strategies raises the technical bar; fewer submissions may mean higher quality.
- Adding trustless settlement via Merkle proofs and CPI on Solana can be a differentiator in Track 1. — Optional features are specifically mentioned as desirable by judges.
- Mainstream consumer apps (Track 2) likely benefit from Solana-native sign-in to simplify UX and meet the requirement. — Sign-up through Solana is mandatory; using it elegantly can improve polish.
- The product must go beyond a simple dashboard; judges value original interaction models and end-to-end execution. — Track 2 explicitly values 'original consumer interaction models' and 'complete end-to-end execution'.
- Data dashboards alone are unlikely to win without real-time features or irreversible state changes. — The brief warns against wireframes/pitch decks; a static dashboard may be seen as insufficient.

## Missing
- Detailed judging criteria breakdown by weight/percentage per track.
- Prior year winning project names and descriptions (to avoid duplication).
- TxLINE API technical specifications (rate limits, schema details, authentication).
- Clarity on 'API feedback' requirement format.
- Whether Solana mainnet or devnet is required/preferred for deployment.
- Size and background of the judging panel.
- Per-track or overall winner limits per participant.
- Bonus prizes or sponsor-specific awards beyond the three tracks.
- Exact rules on using other data sources alongside TxLINE.
- Observed submission numbers source and recency (may be historical).

## Potentially stale
- Observed submission counts (112, 113, 91) may reflect a previous edition, not this hackathon's expected volume.
- Free TxLINE access guarantee may change if the provider updates terms before the hackathon start.
- TxLINE credit token restriction details could be revised.

## Crowding map
### High collision
- Direct sports betting platform
- Prediction market with AMM
- Live score dashboard without additional value
- AI pundit bot (listed example)
- Group sweepstakes app
- Hi-lo stats game
- Sharp movement detector agent
- In-play market maker agent
- Parametric sports insurance product
- Sportsbook UI clone
### Medium collision
- Prop bet market with minor variations
- Betting arbitrage scanner
- Odds visualization dashboard with basic filters
- Social betting with standard UX
- Automated betting executor without novel strategy
- Recent similar title: GoalGate-Jamhacks10
- Recent similar title: LSUDOKO
- Recent similar title: Flexy
### Potentially underexplored
- Real-time sports data-driven game with irreversible state changes
- Trustless dispute resolution for sports data oracles
- Compliance and regulatory automation for betting platforms
- AI agent that generates dynamic sports highlights from live data
- Fan engagement via staking or loyalty using live match metrics
- Manipulation detection system for odds feeds
- Solana-native data streaming proof verification for DePIN
- Decentralized commentary platform with prediction incentives
- Event-driven NFT minting based on match events
### Do not build
- Products that use TxLINE credit token for user wagering or transfers
- Wireframes or pitch decks without a working build
- Projects with no TxLINE data dependency
- Pure gambling apps that obviously violate legal restrictions
- Dashboard-only analytics without an irreversible state change or novel interaction
