def serialize_labels(labels):
  if not labels:
    return ""

  inside = ', '.join([f"{key}=\"{val}\"" for (key, val) in labels.items()])
  return '{' + inside + '}'

class Metric:
  help_text = None
  metric_name = None
  metric_type = None
  value = None

  def __init__(self, n, t, h):
    self.metric_name = n
    self.metric_type = t
    self.help_text = h

  def print_metrics(self, new_value = None, labels = {}):
    if new_value:
      self.value = new_value

    return self.print_help_text() + self.print_value_text(new_value, labels)

  def print_help_text(self):
    return [
      f"# HELP {self.metric_name} {self.help_text}",
      f"# TYPE {self.metric_name} {self.metric_type}"
    ]

  def print_value_text(self, new_value = None, labels = {}):
    if new_value:
      self.value = new_value

    return [f"{self.metric_name}{serialize_labels(labels)} {self.value or 0}"]
    

  def set_value(self, v):
    self.value = v
