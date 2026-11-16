#![no_std]
#![forbid(unsafe_code)]

pub mod descriptor;
pub mod hid;
pub mod input;
pub mod activation;
pub mod xhci;
pub mod completion;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod activation_tests;
#[cfg(test)]
mod completion_tests;
