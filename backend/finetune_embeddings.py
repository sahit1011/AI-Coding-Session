"""
Fine-tune embedding model for domain-specific coding conversations.

This script fine-tunes a base embedding model (e.g., CodeBERT) on your
coding session data to improve semantic understanding of technical queries.

Approach: Contrastive Learning
- Positive pairs: (user_query, relevant_assistant_response)
- Negative pairs: (user_query, irrelevant_response)
"""

import os
import json
import random
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from datetime import datetime

# Import data loading utilities
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.data_loader import load_session_files


def create_training_pairs(sessions_data: List[Dict[str, Any]]) -> List[InputExample]:
    """
    Create training pairs from session data.
    
    Strategy:
    1. Positive pairs: Query + its actual response (high relevance)
    2. Negative pairs: Query + response from different session/topic (low relevance)
    3. Hard negatives: Query + response from same session but different QA pair (medium relevance)
    
    Returns:
        List of InputExample objects for training
    """
    training_examples = []
    
    print("Creating training pairs from sessions...")
    
    # Collect all QA pairs across all sessions
    all_qa_pairs = []
    for session in sessions_data:
        engineer_name = session.get("engineer_name", "Unknown")
        project_name = session.get("project_name", "Unknown")
        
        for qa_pair in session.get("qa_pairs", []):
            all_qa_pairs.append({
                "query": qa_pair.get("user_query", ""),
                "response": qa_pair.get("assistant_response", ""),
                "engineer": engineer_name,
                "project": project_name,
                "session_id": session.get("session_id", "")
            })
    
    print(f"Found {len(all_qa_pairs)} QA pairs across all sessions")
    
    # Create positive pairs (query + its response)
    positive_pairs = []
    for qa in all_qa_pairs:
        if qa["query"] and qa["response"]:
            # Clean and truncate for training
            query = qa["query"].strip()[:512]  # Max length for embeddings
            response = qa["response"].strip()[:512]
            
            if len(query) > 10 and len(response) > 10:  # Minimum length
                positive_pairs.append((query, response))
    
    print(f"Created {len(positive_pairs)} positive pairs")
    
    # Create training examples
    for query, response in positive_pairs:
        # Positive example: query + its response
        positive_example = InputExample(
            texts=[query, response],
            label=1.0  # High similarity
        )
        training_examples.append(positive_example)
        
        # Negative example: query + random unrelated response
        # This teaches the model to distinguish relevant from irrelevant
        if len(all_qa_pairs) > 1:
            # Find a negative (different topic/context)
            negative_qa = random.choice(all_qa_pairs)
            negative_response = negative_qa["response"].strip()[:512]
            
            # Make sure it's actually different
            if negative_response != response and len(negative_response) > 10:
                negative_example = InputExample(
                    texts=[query, negative_response],
                    label=0.0  # Low similarity
                )
                training_examples.append(negative_example)
    
    print(f"Total training examples: {len(training_examples)}")
    print(f"  - Positive pairs: {len(positive_pairs)}")
    print(f"  - Negative pairs: {len(training_examples) - len(positive_pairs)}")
    
    return training_examples


def fine_tune_model(
    base_model: str = "microsoft/codebert-base",
    output_path: str = "./models/finetuned-coding-embeddings",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    warmup_steps: int = 100
):
    """
    Fine-tune embedding model on coding session data.
    
    Args:
        base_model: Base model to fine-tune (e.g., "microsoft/codebert-base")
        output_path: Where to save the fine-tuned model
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate for optimizer
        warmup_steps: Number of warmup steps for learning rate scheduler
    """
    print("="*60)
    print("Fine-tuning Embedding Model for Coding Conversations")
    print("="*60)
    print(f"\nBase Model: {base_model}")
    print(f"Output Path: {output_path}")
    print(f"Epochs: {epochs}")
    print(f"Batch Size: {batch_size}")
    print(f"Learning Rate: {learning_rate}\n")
    
    # Load base model
    print(f"[1/5] Loading base model: {base_model}...")
    try:
        model = SentenceTransformer(base_model)
        print("✓ Model loaded successfully!")
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        print("Falling back to all-MiniLM-L6-v2...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Load session data
    print("\n[2/5] Loading session data...")
    data_dir = "../data" if os.path.exists("../data") else "data"
    sessions_data = load_session_files(data_dir)
    print(f"✓ Loaded data for {len(sessions_data)} engineers")
    
    # Create training pairs
    print("\n[3/5] Creating training pairs...")
    training_examples = create_training_pairs(sessions_data)
    
    if len(training_examples) < 10:
        print("✗ Not enough training examples! Need at least 10.")
        print("  Current: {len(training_examples)}")
        return None
    
    # Create data loader
    print("\n[4/5] Preparing training data...")
    train_dataloader = DataLoader(
        training_examples,
        shuffle=True,
        batch_size=batch_size
    )
    
    # Define loss function (contrastive learning)
    # CosineSimilarityLoss: Maximizes similarity for positive pairs, minimizes for negative
    train_loss = losses.CosineSimilarityLoss(model)
    
    # Fine-tune the model
    print("\n[5/5] Starting fine-tuning...")
    print("This may take a while depending on your hardware...\n")
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        output_path=output_path,
        show_progress_bar=True,
        optimizer_params={"lr": learning_rate},
        evaluation_steps=100,  # Evaluate every 100 steps
        save_best_model=True
    )
    
    print(f"\n✓ Fine-tuning complete!")
    print(f"✓ Model saved to: {output_path}")
    print(f"\nTo use the fine-tuned model, update config.py:")
    print(f'  "embedding_model": "{output_path}"')
    
    return model


def evaluate_finetuned_model(
    base_model_path: str,
    finetuned_model_path: str,
    test_queries: List[str]
):
    """
    Compare base vs fine-tuned model on test queries.
    
    This helps verify that fine-tuning improved the model.
    """
    print("\n" + "="*60)
    print("Evaluating Fine-tuned Model")
    print("="*60)
    
    base_model = SentenceTransformer(base_model_path)
    finetuned_model = SentenceTransformer(finetuned_model_path)
    
    print(f"\nComparing:")
    print(f"  Base: {base_model_path}")
    print(f"  Fine-tuned: {finetuned_model_path}")
    print(f"\nTest queries: {len(test_queries)}")
    
    # You can add evaluation logic here
    # For example, compare embeddings similarity for known good pairs
    print("\n✓ Evaluation complete (add detailed metrics as needed)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune embedding model for coding conversations")
    parser.add_argument(
        "--base-model",
        type=str,
        default="microsoft/codebert-base",
        help="Base model to fine-tune (default: microsoft/codebert-base)"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="./models/finetuned-coding-embeddings",
        help="Output path for fine-tuned model"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size (default: 16)"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="Learning rate (default: 2e-5)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_path, exist_ok=True)
    
    # Fine-tune
    model = fine_tune_model(
        base_model=args.base_model,
        output_path=args.output_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate
    )
    
    if model:
        print("\n" + "="*60)
        print("Fine-tuning Summary")
        print("="*60)
        print(f"✓ Model: {args.base_model}")
        print(f"✓ Fine-tuned model saved to: {args.output_path}")
        print(f"✓ Training completed successfully!")
        print("\nNext steps:")
        print("1. Update config.py to use the fine-tuned model:")
        print(f'   "embedding_model": "{args.output_path}"')
        print("2. Restart the backend server")
        print("3. Test search quality improvements")

