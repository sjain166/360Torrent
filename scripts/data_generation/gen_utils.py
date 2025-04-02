import numpy as np
import os
import bisect

dbg_print = False


ZIPF_ALPHA = 1.01 # skewness param
ZIPF_SIZE = 1 # draw one element from the distribution at any time
ZIPF_N = 10**4 # Reasonable cap on zipf distribution draws for simulation experiments

def zipf_rank_to_probability(rank):
    harmonic_sum = np.sum(1 / np.arange(1, ZIPF_N + 1) ** ZIPF_ALPHA)
    return (1 / rank**ZIPF_ALPHA) / harmonic_sum

def draw_content_from_roster(user):
    PRINT_HERE = True

    if len(user["content_roster"]) == 0: return None

    popularities = np.array([c["popularity"] for c in user["content_roster"]])

    probabilities = np.array([ zipf_rank_to_probability(p) for p in popularities] )
    probabilities /= np.sum(probabilities)

    if dbg_print and PRINT_HERE:
        print()
        print(f" Entering draw to user {user["id"]}")
        print(f" User {user["id"]} roster {user["content_roster"]}")
        print(f" Rank:Probability {list(zip(popularities, probabilities))}")

    drawn = np.random.choice(user["content_roster"], p=(probabilities))

    if dbg_print and PRINT_HERE:
        print(f" User {user["id"]} draws {drawn}")

    user["content_roster"].remove(drawn)

    if len(user["content_roster"]) > 0:
        new_popularities = np.array([c["popularity"] for c in user["content_roster"]]) # Re-create popularities excluding our drawn object
        new_popularities = new_popularities * ZIPF_N / new_popularities.sum() # Normalize
        new_popularities = np.clip([int(p) for p in new_popularities], a_min=1, a_max=None) # Make sure popularity ranks are integers
        for c, p in enumerate(new_popularities):
            user["content_roster"][c]["popularity"] = p # Re-assign popularities to each file

    return drawn

def push_content_to_roster(user, new_content):
    PRINT_HERE = True
    if len(user["content_roster"]) == 0:
        user["content_roster"].append(new_content)
        return

    if dbg_print and PRINT_HERE:
        print()
        print(f" Entering push to {user["id"]}")
        print(f" User {user["id"]} roster {user["content_roster"]}")
        print(f" Content {new_content}")

    roster_sorted_by_popularity = sorted(user["content_roster"], key=lambda c: c["popularity"]) # Sort list s.t. low ranks (more popular) are at the front

    old_popularities = np.array([c["popularity"] for c in roster_sorted_by_popularity])
    new_content_idx = bisect.bisect_left(old_popularities, new_content["popularity"]) # Index where the new_content's rank belongs in the sorted array
    popularities = np.insert(old_popularities, new_content_idx, new_content["popularity"])

    popularities = popularities * ZIPF_N / popularities.sum() # Normalize
    popularities = np.clip([int(p) for p in popularities], a_min=1, a_max=None) # Make sure ranks are ints

    if dbg_print and PRINT_HERE:
        print(f" popularities pre-insert {old_popularities}")
        print(f" popularities post-insert {popularities}")

    roster_sorted_by_popularity.insert(new_content_idx, new_content) # Place new content at its proper index in the roster
    for c in range(len(roster_sorted_by_popularity)):
        roster_sorted_by_popularity[c]["popularity"] = popularities[c] # Map new popularities to content in roster

    user["content_roster"] = roster_sorted_by_popularity # Update content roster with new shifted and sorted roster

