import logging
import os
import time
from dataclasses import dataclass
from logging import Logger
from typing import Any

import joblib
import numpy as np
from injector import inject, Module, provider, ClassAssistedBuilder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from decai.simulation.contract.classification.classifier import Classifier


# Purposely not a singleton so that it is easy to get a model that has not been initialized.
@inject
@dataclass
class SciKitClassifier(Classifier):
    """
    Classifier for a scikit-learn like model.
    """

    _logger: Logger
    _model_initializer: Any

    def __post_init__(self):
        self._model = None
        self._original_model_path = f'saved_models/{time.time()}-{id(self)}.joblib'

    def evaluate(self, data, labels) -> float:
        assert self._model is not None, "The model has not been initialized yet."
        assert isinstance(data, np.ndarray), "The data must be an array."
        assert isinstance(labels, np.ndarray), "The labels must be an array."
        self._logger.debug("Evaluating.")
        return self._model.score(data, labels)

    def log_evaluation_details(self, data, labels, level=logging.INFO) -> float:
        assert self._model is not None, "The model has not been initialized yet."
        assert isinstance(data, np.ndarray), "The data must be an array."
        assert isinstance(labels, np.ndarray), "The labels must be an array."
        self._logger.debug("Evaluating.")
        predicted_labels = self._model.predict(data)
        result = accuracy_score(labels, predicted_labels)
        if self._logger.isEnabledFor(level):
            m = confusion_matrix(labels, predicted_labels)
            report = classification_report(labels, predicted_labels)
            self._logger.log(level,
                             "Confusion matrix:\n%s"
                             "\nReport:\n%s"
                             "\nAccuracy: %0.2f%%",
                             m, report, result * 100)
        return result

    def init_model(self, training_data, labels):
        assert self._model is None, "The model has already been initialized."
        self._logger.debug("Initializing model.")
        self._model = self._model_initializer()

        self._model.fit(training_data, labels)
        self._logger.debug("Saving model to \"%s\".", self._original_model_path)
        os.makedirs(os.path.dirname(self._original_model_path), exist_ok=True)
        joblib.dump(self._model, self._original_model_path)

    def predict(self, data):
        assert self._model is not None, "The model has not been initialized yet."
        assert isinstance(data, np.ndarray), "The data must be an array."
        return self._model.predict([data])[0]

    def update(self, data, classification):
        assert self._model is not None, "The model has not been initialized yet."
        self._model.partial_fit([data], [classification])

    def reset_model(self):
        assert self._model is not None, "The model has not been initialized yet."
        self._logger.debug("Loading model from \"%s\".", self._original_model_path)
        self._model = joblib.load(self._original_model_path)


@dataclass
class SciKitClassifierModule(Module):
    _model: Any

    # Purposely not a singleton so that it is easy to get a model that has not been initialized.
    @provider
    def provide_classifier(self, builder: ClassAssistedBuilder[SciKitClassifier]) -> Classifier:
        return builder.build(
            _model_initializer=lambda: self._model,
        )
