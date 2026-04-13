import os
import pymupdf4llm
import litellm
from pathlib import Path

# Helper to ensure environment variables are loaded
def setup_env():
    # LiteLLM looks for OPENAI_API_KEY in the environment.
    # If not set in your shell, you can set it here:
    # os.environ["OPENAI_API_KEY"] = "sk-..."
    pass

class PolicyAgent:
    def __init__(self, pdf_path: str = "data/2026AnthemgHIPSBC.pdf") -> None:
        setup_env()
        self.pdf_path = pdf_path
        
        if not Path(self.pdf_path).exists():
            raise FileNotFoundError(f"Could not find PDF at {self.pdf_path}")

        print(f"[*] Extracting policy data from {self.pdf_path}...")
        
        # FIX: We use write_layout=True to ensure the columns stay aligned.
        # This keeps 'Deductible' horizontally linked to the '$' amounts.
        self.policy_context = pymupdf4llm.to_markdown(
            doc=self.pdf_path,
            write_layout=True,  
            header=False,
            footer=False
        )
        
        # Audit Log for AppSec debugging
        with open("debug_context.md", "w") as f:
            f.write(self.policy_context)
            
        print(f"[+] Extraction complete. Context size: {len(self.policy_context)} characters.")

    def answer_query(self, prompt: str) -> str:
        try:
            # We use the 'Instruction Sandwich' pattern.
            # In 2026, placing rules AFTER the data block significantly increases accuracy.
            response = litellm.completion(
                model="openai/gpt-4o-mini",
                max_tokens=1000,
                temperature=0,  # Zero temperature ensures factual consistency
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a specialized Insurance Policy Auditor. "
                            "You are an expert at parsing Markdown tables and SBC documents."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"### POLICY DATA START ###\n{self.policy_context}\n### DATA END ###\n\n"
                            f"USER QUESTION: {prompt}\n\n"
                            "### EXTRACTION RULES:\n"
                            "1. Look for the 'Important Questions' table near the top of the data.\n"
                            "2. Locate the row titled 'What is the overall deductible?'.\n"
                            "3. Look in the 'Answers' column. Identify the separate amounts for 'In-Network' and 'Out-of-Network'.\n"
                            "4. Provide the exact dollar amounts found. If the info is missing, say 'I don't know'."
                        ),
                    },
                ],
            )
            
            content = response.choices[0].message.content
            # LaTeX formatting fix for dollar signs (renders correctly in UI)
            return content.replace("$", r"\$")
            
        except Exception as e:
            return f"Error during inference: {str(e)}"

# Integrated Test Runner
if __name__ == "__main__":
    # Ensure you have run: pip install pymupdf4llm litellm
    agent = PolicyAgent()
    
    # This specific query targets the SBC table we saw in your grep output
    test_query = "What is the deductible for individual and family, both In-Network and Out-of-Network?"
    print(f"\n[?] Querying: {test_query}")
    
    result = agent.answer_query(test_query)
    print(f"\n[!] Agent Response:\n{result}")
