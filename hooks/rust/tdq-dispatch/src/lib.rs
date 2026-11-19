//! tdq-dispatch: native hook router and Hot-path dispatcher for Antigravity 2.0.

pub mod command_parser;
pub mod events;
pub mod lock;
pub mod protocol;
pub mod storage;

/// Hybrid routing decision returned by Rust event handlers.
#[derive(Debug, Clone, PartialEq)]
pub enum RouteOutcome {
    /// Event was resolved synchronously in Rust Hot-path.
    Decided(protocol::HookDecision),
    /// Cold-path or complex case requires delegation to Python `hooks/scripts/dispatch.py`.
    DelegatePython,
}

/// Return crate version embedded at compile time.
pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert_eq!(version(), env!("CARGO_PKG_VERSION"));
        assert!(!version().is_empty());
    }
}
