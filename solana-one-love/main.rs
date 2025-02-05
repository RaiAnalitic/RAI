// src/main.rs

use std::process::Command;
use std::fs;
use std::env;

fn main() {
    let script = "console.log('RAI SOLANA SCANNER');";
    let file_path = "script.html";
    
    let html_content = format!(
        "<html><body><script>{}</script></body></html>",
        script
    );
    
    fs::write(file_path, html_content).expect("Unable to write file");
    
    let _ = Command::new("xdg-open") // Linux
        .arg(file_path)
        .status()
        .or_else(|_| Command::new("open") // macOS
            .arg(file_path)
            .status())
        .or_else(|_| Command::new("cmd") // Windows
            .args(["/C", "start", file_path])
            .status());
    
    println!("Opening browser with RAI SOLANA SCANNER...");
}
