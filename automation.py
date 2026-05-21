"""
Optimized Gmail Automation Script

This script automates the process of:
1. Fetching removal links from Gmail
2. Processing them via Selenium

Features:
- Pagination support for Gmail API
- Rate limiting with exponential backoff
- Headless browser mode
- Parallel processing capability
- Comprehensive logging
- Error recovery
"""
import logging
import sys
from datetime import datetime
from typing import List, Tuple
import config
from gmail_handler import GmailHandler
from selenium_handler import SeleniumHandler


def setup_logging() -> None:
    """Configure logging for the application"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)


def print_summary(results: List[Tuple[str, bool, str]]) -> None:
    """
    Print summary of processing results
    
    Args:
        results: List of (link, success, message) tuples
    """
    total = len(results)
    successful = sum(1 for _, success, _ in results if success)
    failed = total - successful
    
    print("\n" + "="*70)
    print("PROCESSING SUMMARY")
    print("="*70)
    print(f"Total links processed: {total}")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    print(f"Success rate: {(successful/total*100):.1f}%" if total > 0 else "N/A")
    
    if failed > 0:
        print("\nFailed links:")
        for link, success, message in results:
            if not success:
                print(f"  - {link}")
                print(f"    Reason: {message}")
    
    print("="*70)


def save_results(results: List[Tuple[str, bool, str]], filename: str = None) -> None:
    """
    Save processing results to a file
    
    Args:
        results: List of (link, success, message) tuples
        filename: Output filename (default: results_TIMESTAMP.txt)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Gmail Automation Results\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("="*70 + "\n\n")
            
            for link, success, message in results:
                status = "SUCCESS" if success else "FAILED"
                f.write(f"[{status}] {link}\n")
                f.write(f"  Message: {message}\n\n")
            
            # Summary
            total = len(results)
            successful = sum(1 for _, success, _ in results if success)
            f.write("\n" + "="*70 + "\n")
            f.write("SUMMARY\n")
            f.write(f"Total: {total}\n")
            f.write(f"Successful: {successful}\n")
            f.write(f"Failed: {total - successful}\n")
        
        logging.info(f"Results saved to {filename}")
        
    except Exception as e:
        logging.error(f"Failed to save results: {e}")


def save_deleted_messages_log(
    deleted_message_ids: List[str],
    link_to_messages: dict,
    message_metadata: dict,
    results: List[Tuple[str, bool, str]],
    timestamp: str = None
) -> None:
    """
    Save deleted message IDs and their associated links to a log file
    
    Args:
        deleted_message_ids: List of message IDs that were deleted
        link_to_messages: Mapping of links to message IDs
        message_metadata: Mapping of message IDs to metadata (subject, date)
        results: Processing results to show why each was deleted
        timestamp: Timestamp string for filename (default: current time)
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"deleted_log_{timestamp}.txt"
    
    try:
        # Create reverse mapping: message_id -> links
        message_to_links = {}
        for link, msg_ids in link_to_messages.items():
            for msg_id in msg_ids:
                if msg_id not in message_to_links:
                    message_to_links[msg_id] = []
                message_to_links[msg_id].append(link)
        
        # Create mapping of link -> result
        link_results = {link: (success, message) for link, success, message in results}
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n" + "="*70 + "\n")
            f.write(f"Deletion Log - {datetime.now().isoformat()}\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Total messages deleted: {len(deleted_message_ids)}\n\n")
            
            for msg_id in deleted_message_ids:
                f.write(f"Message ID: {msg_id}\n")
                
                # Add message metadata
                if msg_id in message_metadata:
                    metadata = message_metadata[msg_id]
                    f.write(f"  Subject: {metadata.get('subject', 'No Subject')}\n")
                    f.write(f"  Date: {metadata.get('date', 'Unknown')}\n")
                
                # List all links from this message
                if msg_id in message_to_links:
                    f.write(f"  Associated Links ({len(message_to_links[msg_id])}):\n")
                    for link in message_to_links[msg_id]:
                        f.write(f"    - {link}\n")
                        # Show processing result for this link
                        if link in link_results:
                            success, message = link_results[link]
                            status = "SUCCESS" if success else "FAILED"
                            f.write(f"      Status: [{status}] {message}\n")
                
                f.write("\n")
            
            f.write("="*70 + "\n\n")
        
        logging.info(f"Deletion log saved to {filename}")
        
    except Exception as e:
        logging.error(f"Failed to save deletion log: {e}")


def main():
    """Main execution function"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*70)
    logger.info("Gmail Automation Script Started")
    logger.info("="*70)
    
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    
    try:
        # Step 1: Fetch removal links from Gmail
        logger.info("Step 1: Fetching removal links from Gmail")
        gmail = GmailHandler()
        links, link_to_messages, message_metadata = gmail.get_removal_links()
        
        if not links:
            logger.warning("No removal links found. Exiting.")
            return
        
        logger.info(f"Found {len(links)} unique removal links")
        
        # Step 2: Process links with Selenium
        logger.info("Step 2: Processing links with Selenium")
        selenium = SeleniumHandler(headless=config.HEADLESS_MODE)
        results = selenium.process_links(links)
        
        # Step 3: Delete emails after processing
        logger.info("Step 3: Deleting processed emails")
        messages_to_delete = set()
        
        for link, success, message in results:
            # Delete emails if:
            # 1. Successfully removed (success=True)
            # 2. Remove button not found (likely expired/already processed)
            if success or "not found" in message.lower():
                if link in link_to_messages:
                    messages_to_delete.update(link_to_messages[link])
                    logger.debug(f"Marking {len(link_to_messages[link])} message(s) for deletion for link: {link[:50]}...")
        
        if messages_to_delete:
            deleted_message_list = list(messages_to_delete)
            deleted_count = gmail.delete_messages_batch(deleted_message_list)
            logger.info(f"Deleted {deleted_count} email(s) from Gmail")
            
            # Save deletion log with metadata and timestamp
            save_deleted_messages_log(deleted_message_list, link_to_messages, message_metadata, results, timestamp)
        else:
            logger.info("No emails to delete")
        
        # Step 4: Generate summary and save results
        logger.info("Step 4: Generating summary")
        print_summary(results)
        save_results(results)
        
        # Calculate execution time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Total execution time: {duration:.2f} seconds")
        
        logger.info("="*70)
        logger.info("Gmail Automation Script Completed Successfully")
        logger.info("="*70)
        
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
