#![no_std]
#![forbid(unsafe_code)]

pub mod descriptor;
pub mod hid;
pub mod input;
pub mod activation;
pub mod xhci;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod activation_tests;
