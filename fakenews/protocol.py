# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import bittensor as bt
import pydantic


class ArticleSynapse(bt.Synapse):
    """
    A protocol representation which uses bt.Synapse as its base.
    This protocol helps in handling request and response communication between
    the miner and the validator.

    Attributes:
    - articles_to_review: List of article texts that need to be checked for fake news
    - original_article: The original article text
    - fake_probabilities: List of miner-assigned probabilities for each article

    """

    articles_to_review: list[str] = pydantic.Field(
        ...,
        title="Articles to Review",
        description="A list of article texts to review. Immutable.",
        allow_mutation=False,
    )

    original_article: str | None = pydantic.Field(
        None,
        title="Original Article",
        description="The original article text. Immutable, Nullable.",
        allow_mutation=False,
    )

    fake_probabilities: list[float] = pydantic.Field(
        ...,
        title="Fake probabilities",
        description="""A list of fake probabilities for the articles. Miners should assign each article a rating between 0 and 1,
            where 0 indicates a completely true and credible article, and 1 indicates a completely fabricated article with no credible facts.
            This attribute is mutable and should be updated by the miner.""",
        allow_mutation=True,
    )

    def deserialize(self) -> list[float]:
        """
        Deserialize output. This method retrieves the response from
        the miner in the form of self.text, deserializes it and returns it
        as the output of the dendrite.query() call.

        Returns:
        - List[float]: The deserialized response, which in this case is the list of preidictions.
        """
        return self.fake_probabilities
