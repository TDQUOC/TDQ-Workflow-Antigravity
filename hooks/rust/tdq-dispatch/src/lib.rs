//! tdq-dispatch: native hook dispatcher for Antigravity

pub mod command_parser;
pub mod events;
pub mod lock;
pub mod protocol;
pub mod storage;

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert_eq!(version(), "0.1.0");
    }
}
