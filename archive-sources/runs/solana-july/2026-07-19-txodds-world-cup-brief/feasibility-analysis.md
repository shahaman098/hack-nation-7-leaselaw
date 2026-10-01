# Feasibility analysis

## concept-group-crypto-call
- Delivery risk: **high**
- Kill?: False
- Non-fakeable core: Solana program that verifies a stat via CPI to TxLINE and conditionally mints based on outcome.
- Min demo loop: Submit one hardcoded prediction text, mock TxLINE update, trigger on-chain resolution, and display NFT receipt in wallet.
- Dependencies: Working Solana CPI call to TxLINE validate_stat instruction, which may not exist or be documented for devnet., GPT-5.6 natural-language-to-constraint reliability under adversarial or ambiguous predictions (e.g., 'Mbappé hat trick' vs own goal)., Solana NFT mint with soulbound attributes requiring token-2022 or custom program, not a trivial devnet deployment.
- Notes: The killer demo describes a Solana app that reads TxLINE and auto-mints NFTs. Without TxLINE API docs for CPI, the team is building against an imaginary interface. Risk collapses if TxLINE test harness ships with a validate_stat equivalent on devnet; otherwise the demo loop is fakeable but the core mechanism is vapor.

## conc-feat-health
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Continuous Merkle root computation over windows and on-chain verification of the root.
- Min demo loop: Feed a pre-cut fixture with a gap, compute two Merkle roots, store one on-chain, detect mismatch, emit console alert.
- Dependencies: TxLINE data format and availability: must have a stream or fixture that can be ingested in a sliding-window fashion; a single JSON dump is insufficient., On-chain Merkle root storage Solana program; writing, deploying, and debugging a new program on devnet within 5 days is tight., GPT-5.6 role is unclear—Merkle tree construction and comparison is deterministic; depending on it for anomaly threshold introduces non-reproducibility.
- Notes: Feasible if the team has strong Solana and Merkle tree experience. The GPT-5.6 dependency is artificial—this is pure signal processing. The risk is over-engineering: trying to integrate GPT-5.6 will waste time. A tight Rust/Python loop without LLM is more likely to ship.

## concept-1
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Merkle proof generation from TxLINE data and on-chain verification returning boolean validity.
- Min demo loop: Load a known TxLINE Merkle root on-chain, reconstruct proof for one stat, submit CPI call, log pass/fail.
- Dependencies: Access to full TxLINE Merkle tree leaf data off-chain to compute proofs; a public RPC or API must provide this in devnet., On-chain Keccak-256 hash verification via CPI or syscall; team must confirm compatibility with Solana's built-in hash functions., A mock 'settled bet' fixture that the verifier can correctly disprove, requiring at least one prebuilt valid proof.
- Notes: This is the most self-contained candidate and does not require an LLM—it is a pure crypto engineering problem. The main risk is TxLINE's Merkle tree structure and data availability. If TxLINE already publishes roots on-chain and the leaf encoding is documented, this is a solid demo. Otherwise, it's a guessing game.

## conc-replay-sandbox
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Stream a sequence of TxLINE-formatted data points at a configurable rate and trigger downstream contract resolution.
- Min demo loop: Load a small JSON fixture, stream it at 5x speed to a mock prediction market program, show resolved outcome matching fixture.
- Dependencies: A realistic World Cup historical JSON fixture in TxLINE-compatible schema; the cited source (devpost portfolio) is unrelated to sports data., Solana program that records replay provenance via CPI; writing and deploying a non-trivial program in 5 days is risky., Configurable replay server with timing control; building a reliable stream simulator with speed multiplier requires careful engineering.
- Notes: The idea has genuine hackathon utility, but the cited data source is completely wrong—it is a personal portfolio, not sports data. The team must find or fabricate a World Cup fixture. The provenance program is overkill; dropping it reduces risk significantly. The core value is a simple replay server, which is a 1-day build.
