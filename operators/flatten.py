from datetime import datetime

def flatten_results(results: list) -> list:
	"""
	Flatten the results list so each nomination is a row, with columns for announcement and nomination keys.
	"""
	flat_rows = []
	nomination_keys = ["name_rank", "name", "rank", "promotion_grade", "new_assignment", "current_assignment", "location"]

	for result in results:
		# Format date_published to just the date part if it's a datetime object
		date_published = result["date_published"]
		if isinstance(date_published, datetime):
			date_published = date_published.strftime("%Y-%m-%d")
		
		base = {
			"announcement_title": result["announcement_title"],
			"date_published": date_published,
			"summary": result["summary"],
			# 'body' intentionally excluded from flattened output
			"link": result["link"],
		}
		nominations = result.get("nominations", [])
		if nominations:
			for nom in nominations:
				row = base.copy()
				# Ensure name_rank is present if possible
				row["name_rank"] = nom.get("name_rank", f"{nom.get('rank','')} {nom.get('name','')}")
				row["name"] = nom.get("name", "")
				row["rank"] = nom.get("rank", "")
				row["promotion_grade"] = nom.get("promotion_grade", "")
				row["new_assignment"] = nom.get("new_assignment", "")
				row["current_assignment"] = nom.get("current_assignment", "")
				row["location"] = nom.get("location", "")
				flat_rows.append(row)
		else:
			# If no nominations, still include the announcement
			row = base.copy()
			flat_rows.append(row)
	return flat_rows
