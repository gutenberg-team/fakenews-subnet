# <h1 align="center">📰 FakeNews - Subnet 🗣️</h1> 

- [📰 FakeNews - Subnet 🗣️](#-fakenews---subnet-️)
  - [Introduction](#introduction)
  - [Roadmap](#roadmap)
  - [List of Miner Tasks](#list-of-miner-tasks)
  - [Validating and Mining](#validating-and-mining)
    - [Validator](#validator)
    - [Miner](#miner)
  - [Reward Mechanism](#reward-mechanism)
  - [License](#license)

## Introduction

FakeNews is a decentralized AI subnet on the Bittensor platform, dedicated to combating misinformation by providing real-time fake news detection and advanced fact-checking capabilities. This subnet aims to deliver the highest possible accuracy, surpassing traditional solutions—even for rapid, real-time verifications. Our vision is to create the world’s most trusted source for news and fact verification, ensuring every user can rely on timely and accurate insights with help and power of decentralized AI community. 

## Roadmap
To develop an advanced news validation and fact-checking system, we have structured our roadmap into three phases. Each phase bringing us closer to delivering the most accurate and efficient solution on the market.

Phase 1
- **Establish a "FakeNews" dataset:** Create a comprehensive dataset of reliable news articles, collected in real time, laying the groundwork for robust model training and validation

- **Testnet Launch & Miner Onboarding:**
Deploy the initial version in a testnet environment, recruiting early miners to help refine system performance under real-world conditions and gather feedback.

- **Baseline Release (82% Accuracy) for miners**


- **Version 1.0 Deployment to Mainnet:**
Launch the subnet on mainnet, allowing broader participation and forming the core infrastructure for further development.

Phase 2
- **Expand Task Complexity & Scope:**
Introduce more challenging fact-checking tasks and diversified datasets to improve both accuracy and miner efficiency.

- **Web App Launch:**
Roll out a web interface, enabling wider community engagement and facilitating real-time requests to miners.
- **Release of a new baseline:**
Improved accuracy and the capability to solve all of the incoming tasks

Phase 3
- **Full-Scale Fact-Checking Solution:**
Integrate advanced features to address the broadest possible spectrum of news and fact-checking needs, aiming to achieve the highest accuracy in the industry.
- **Enhanced App Experience:**
Deliver an improved version of the application with new features
- **Support of new languages:** French, Italian, German, Spanish


## List of Miner Tasks
The subnet will start with Task #1, and additional tasks will be introduced to miners every 2–4 weeks, depending on miners efficiency


- **Task #1. Basic Comparison:**

Send the original article from our dataset alongside one of the following pairs:
1 fake + 1 real article
2 fake articles
2 real articles


- **Task #2. Advanced Comparison:**

A new version of Task #1 that incorporates four different prompts (weak original, strong original, weak fake, strong fake) plus the original prompt.
This variation uses different writing styles to make it more challenging to distinguish fake content from real.


- **Task #3. Reference Identification:**

Provide either a single original article or content from Task #2.
The miner must find 2–3 reliable external links that point to the original information.
Requires creating a list of trusted resources.


- **Task #4. Blind Verification:**

Similar to Task #2, but without access to the original article.
From this point forward, all tasks will be performed without direct access to the original source.


- **Task #5. Fact-Level Checks:**

Send a separate set of facts from our articles.
The miner must determine which are fake or real and find credible references for them.


- **Task #6. Comprehensive Fact Analysis:**

Provide a full article.
The miner must break it down into individual facts, verify their accuracy, locate reliable sources, and assign a final credibility score to the article.

## Validating and Mining

### Validator

Validators are responsible for analyzing and verifying data submitted by miners.

If you are interested in validating, follow this [guide](docs/VALIDATOR.md).

Validators create [tasks](#tasks) every minute.


**Task #1**

Validators retrieve the original article text. This is a reliable article sourced from major, trustworthy publications. Using LLMs, validators create two different versions of the article:
1. A paraphrased version (without altering any facts or details).
2. A fake news article generated from the original text.

These versions are marked as follows:
- 0: Reliable, trustworthy article.
- 1: Fake news.

Miners should score each version of the article on a scale from 0 to 1. 

**NOTE:** Initially, in Version 0, we provide the original article text.

Responses are normalized to a binary view as follows:
- 0..0.5 → 0
- 0.51..1 → 1

### Miner

Miners in the Bittensor subnet are responsible for solving validators' tasks and providing computational resources.

In the baseline solution, LLMs are used to identify and score each article.

If you are interested in mining, follow this [guide](docs/MINER.md).

## Reward Mechanism

Validators store the 250 most recent responses for each miner (500 results). Each response generates two retrospective results (for both paraphrased and generated fake articles).

These retrospective results are used to calculate the final reward score:

$$ 
Reward_{miner} = \sum_{tasks} weight_{task} \times (\alpha \cdot Accuracy_{long_{task}} + (1 - \alpha) \cdot Accuracy_{short_{task}}),
$$

where:

- **Accuracy**: Analytical metric based on the last N results ([see more](https://scikit-learn.org/1.5/modules/generated/sklearn.metrics.accuracy_score.html)). 
  - **Long**: Long-term period window (300 results ~ 150 answers).
  - **Short**: Short-term period window (20 results ~ 10 answers).
  - **NOTE**: Accuracy is counted for the full number of responses. For example, if the window is equal to 300 results, and the miner is new and answered the very first task correctly, then his accuracy equal `1.0` will be multiplied by the coefficient `2 / 300`, because there are only 2 answers in his retrospective history. Thus, a miner with 100% correct answers will get `1.0` as a reward when he answers 150 tasks.
- **α**: Weight for long-term retrospective, set to 0.5.

This approach avoids randomly generating responses and obtaining an emission for the miner, while still ensuring that the miner can obtain an emission if the miner has started to respond correctly. As well as allows new miners who start to answer well to quickly pass the 0.5 reward threshold and then smoothly increase their answers to 1.

This approach is expected to provide healthier and more adequate competition in the subnetwork and reduce dispersion.

## License

This repository is licensed under the MIT License.

```text
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
```
