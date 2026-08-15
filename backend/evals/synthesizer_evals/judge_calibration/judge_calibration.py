from pathlib import Path
from evals.synthesizer_evals.report_generator import generate_markdown_report
from evals.synthesizer_evals.answer_synthesizer_evals import AnswerSynthesizerEvals
from utils.color import Logger
import json
import time
import uuid
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

class SynthesizerJudgeCalibration(Logger):
    """
    A class for calibrating the Answer Synthesizer agent judge.
    """
    name: str = "SynthesizerJudgeCalibration"
    color: str = Logger.PURPLE

    def __init__(self):
        self.evaluator = AnswerSynthesizerEvals()

        self.calibration_data = Path(__file__).parents[4] / "data" / "evals_data" / "synthesizer_judge_calibration_data.json"
        self.execution_result = Path(__file__).parent / "synthesizer_calibration_execution_results.json"
        
        self.evals_report = Path(__file__).parent / "synthesizer_calibration_report.md"

        self.log("AnswerSynthesizer Judge Calibration initialized successfully.")

    def _load_calibration_data(self):
        try:
            with open(self.calibration_data, 'r') as file:
                data = json.load(file)
            self.log("Calibration data loaded successfully.")
            return data
        except Exception as e:
            self.log(f"Error loading calibration data: {e}")
            raise

    def _save_execution_results(self, results: list[dict]):
        try:
            with open(self.execution_result, 'w') as file:
                json.dump(results, file, indent=4)
            self.log("Execution results saved successfully.")
        except Exception as e:
            self.log(f"Error saving execution results: {e}")
            raise

    def _save_markdown_report(self, report):
        try:
            with open(self.evals_report, "w", encoding="utf-8") as f:
                f.write(report)
            self.log(f"Markdown report saved to {self.evals_report}")
        except Exception as e:
            self.log(f"Error saving Markdown report: {e}")
            raise

    def evaluate(self):
        """
        Main loop to evaluate the answer synthesizer agent quality.
        """
        try:
            data = self._load_calibration_data()
            if not data:
                self.log("No calibration data to process.")
                return None

            execution_results = []
            session_id = str(uuid.uuid4()) 

            for item in data:
                exec_result = self.evaluator._evaluate_single_item(item, session_id)
                
                if exec_result:
                    execution_results.append(exec_result)

                # API rate limit buffer
                time.sleep(2) 

            self._save_execution_results(execution_results)
            self.log(f"Execution results saved to {self.execution_result}")

            # Generates the report using the updated markdown report logic
            report = generate_markdown_report(execution_results)
            self._save_markdown_report(report)
            self.log(f"Markdown report generated and saved to {self.evals_report}")

            return execution_results
            
        except Exception as e:
            self.log(f"Error during batch evaluation: {e}")
            return execution_results

if __name__ == "__main__":
    evaluator = SynthesizerJudgeCalibration()
    print(evaluator.evaluate())